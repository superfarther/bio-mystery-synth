"""Gradient-sensitive protein repair adjudication."""

from __future__ import annotations

import random

from bio_mystery_synth.biology import fasta
from bio_mystery_synth.core import (
    AnswerSpec,
    Difficulty,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    RankingAssertion,
    ScenarioSpec,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.advanced_protein import cosine, mutate, normalize, one_hot_logits, structure_text
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import ProteinRepairFamilySpec

_MODEL = "esm2_t6_8M_UR50D"


@register
class ProteinRepairFamily:
    family_id = "protein-repair-adjudication"
    config_model = ProteinRepairFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_candidates=16, sequence_length=140, hotspot_count=16),
        Difficulty.MEDIUM: dict(num_candidates=24, sequence_length=180, hotspot_count=22),
        Difficulty.HARD: dict(num_candidates=32, sequence_length=220, hotspot_count=28),
    }
    tools = (
        "esm2-gradient",
        "esm2-sample",
        "esm2-score",
        "esm2-embedding",
        "esmfold-prediction",
        "usalign-alignment",
        "dssp-secondary-structure",
        "pyrosetta-energy",
        "pyrosetta-sasa",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, ProteinRepairFamilySpec):
            raise TypeError("invalid protein repair family spec")
        rng = random.Random(spec.seed)
        reference = "M" + runtime.generate_sequences("protein", 1, config.sequence_length, spec.seed)[0][1:]
        gradient = runtime.run_tool(
            "esm2-gradient",
            {"logits": one_hot_logits(reference)},
            {"model_checkpoint": _MODEL, "use_ste": True, "batch_size": 16, "seed": spec.seed},
        )
        matrix = gradient["gradient"]
        if matrix is None:
            raise RuntimeError("gradient computation returned no gradient")
        saliency = [sum(abs(value) for value in row) for row in matrix]
        hotspots = sorted(range(3, len(reference) - 3), key=lambda index: (-saliency[index], index))[
            : config.hotspot_count
        ]
        hotspot_set = set(hotspots)
        masked = []
        for index in range(config.num_candidates):
            damaged = list(mutate(reference, 5 + index % 13, rng, hotspot_set))
            count = max(8, config.hotspot_count // 2 + index % (config.hotspot_count // 2 + 1))
            for position in rng.sample(hotspots, min(count, len(hotspots))):
                damaged[position] = "_"
            masked.append("".join(damaged))
        sampled = runtime.run_tool(
            "esm2-sample",
            {"sequences": masked},
            {
                "model_checkpoint": _MODEL,
                "sampling_method": "iterative_refinement",
                "temperature": 0.8,
                "top_p": 0.95,
                "num_steps": 20,
                "strategy": "entropy",
                "batch_size": 8,
                "seed": spec.seed + 1,
            },
        )
        candidates = [item["sequence"] for item in sampled["results"]]
        raw_ids = [f"repair_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        sample_ids = [mapping[raw] for raw in raw_ids]

        language = runtime.run_tool(
            "esm2-score",
            {"sequences": candidates},
            {"model_checkpoint": _MODEL, "batch_size": 16},
        )["scores"]
        embedded = runtime.run_tool(
            "esm2-embedding",
            {"sequences": [reference, *candidates]},
            {"model_checkpoint": _MODEL, "batch_size": 16},
        )["results"]
        reference_embedding = embedded[0]["mean_embedding"]
        similarities = [cosine(reference_embedding, item["mean_embedding"]) for item in embedded[1:]]
        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [reference, *candidates]},
            {"num_recycles": 6, "max_batch_residues": 1320, "seed": spec.seed},
        )["structures"]
        structures = [structure_text(item) for item in predicted]
        secondary = runtime.run_tool("dssp-secondary-structure", {"inputs": structures}, {})["results"]
        energies = runtime.run_tool("pyrosetta-energy", {"inputs": structures}, {})["results"]
        sasa = runtime.run_tool("pyrosetta-sasa", {"inputs": structures}, {})["results"]
        tm_scores = []
        for structure in structures[1:]:
            result = runtime.run_tool(
                "usalign-alignment",
                {"query_structure": structure, "reference_structure": structures[0]},
                {},
            )
            tm_scores.append(float(result["metrics"]["tm_score_structure_2"]))

        perplexity = [float(item["perplexity"]) for item in language]
        energy_per_residue = [float(item["total_energy"]) / config.sequence_length for item in energies[1:]]
        hotspot_sasa = []
        for item in sasa[1:]:
            by_position = {int(row["residue_index"]) - 1: float(row["sasa"]) for row in item["per_residue"]}
            hotspot_sasa.append(sum(by_position.get(position, 0.0) for position in hotspots) / len(hotspots))
        reference_ss = secondary[0]
        ss_similarity = [
            1
            - sum(
                abs(float(item[field]) - float(reference_ss[field])) for field in ("helix_pct", "sheet_pct", "loop_pct")
            )
            / 200
            for item in secondary[1:]
        ]
        components = list(
            zip(
                normalize(perplexity, False),
                normalize(similarities),
                normalize(tm_scores),
                normalize(energy_per_residue, False),
                normalize(hotspot_sasa, False),
                normalize(ss_similarity),
                strict=True,
            )
        )
        scores = {
            sample: 0.2 * lm + 0.15 * emb + 0.25 * tm + 0.15 * energy + 0.15 * burial + 0.1 * ss
            for sample, (lm, emb, tm, energy, burial, ss) in zip(sample_ids, components, strict=True)
        }
        ranking = sorted(sample_ids, key=lambda sample: (-scores[sample], sample))[:5]
        public_files = {
            "data/reference.fasta": fasta([("Repair_reference", reference)]),
            "data/candidates.fasta": fasta(sorted(zip(sample_ids, candidates, strict=True))),
            "data/reference.pdb": structures[0],
            **{
                f"data/candidate_structures/{sample}.pdb": structure
                for sample, structure in zip(sample_ids, structures[1:], strict=True)
            },
        }
        facts = {
            "reference": reference,
            "candidate_sequences": dict(zip(raw_ids, candidates, strict=True)),
            "hotspots_1_based": [index + 1 for index in hotspots],
            "perplexity": dict(zip(sample_ids, perplexity, strict=True)),
            "embedding_cosine": dict(zip(sample_ids, similarities, strict=True)),
            "tm_scores": dict(zip(sample_ids, tm_scores, strict=True)),
            "energy_per_residue": dict(zip(sample_ids, energy_per_residue, strict=True)),
            "hotspot_sasa": dict(zip(sample_ids, hotspot_sasa, strict=True)),
            "secondary_similarity": dict(zip(sample_ids, ss_similarity, strict=True)),
            "scores": scores,
            "top_five": ranking,
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts=facts,
                anonymization_map=mapping,
                evidence={
                    "gradient": gradient,
                    "sampling": sampled,
                    "language_scores": language,
                    "embeddings": embedded,
                    "predictions": predicted,
                    "secondary_structure": secondary,
                    "energies": energies,
                    "sasa": sasa,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[RankingAssertion(field="top_five_repairs", expected=ranking)],
                rubric_text="Credit requires the five best repairs in order: " + " > ".join(ranking),
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Prioritize repaired proteins across sequence, sensitivity, fold, and stability evidence",
                public_files=sorted(public_files),
                answer_format="top_five: Sample_... > Sample_... > Sample_... > Sample_... > Sample_...",
                default_question=(
                    "The anonymous repair panel, its common reference, and corresponding coordinate models are "
                    "under `data/`. Rank the five repairs most likely to restore a robust member of the reference "
                    "family. Reconcile whole-sequence plausibility, representation-space proximity, sensitivity "
                    "of the reference sequence landscape, preservation of the global fold and secondary-structure "
                    "balance, whole-structure physical energy, and burial of sensitive sites. A candidate that "
                    "excels on only one evidence class should not outrank a consistently supported repair."
                ),
            ),
        )


PROTEIN_REPAIR_FAMILY = ProteinRepairFamily()
