"""Long-horizon protein bridge triage family."""

from __future__ import annotations

import hashlib
import random
from itertools import pairwise

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
    SetAssertion,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import ProteinBridgeFamilySpec


def _structure_text(value: dict[str, object]) -> str:
    structure = value.get("structure")
    if not isinstance(structure, str):
        raise RuntimeError("ESMFold returned no structure text")
    return structure


def _aligned_identity(left: str, right: str) -> float:
    pairs = [(a, b) for a, b in zip(left, right, strict=True) if a != "-" and b != "-"]
    return sum(a == b for a, b in pairs) / len(pairs)


@register
class ProteinBridgeFamily:
    family_id = "protein-bridge-triage"
    config_model = ProteinBridgeFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_candidates=6, sequence_length=100, shortlist_size=3),
        Difficulty.MEDIUM: dict(num_candidates=8, sequence_length=140, shortlist_size=4),
        Difficulty.HARD: dict(num_candidates=8, sequence_length=180, shortlist_size=4),
    }
    tools = (
        "random-protein-sample",
        "esmfold-prediction",
        "structure-metrics",
        "tmalign-alignment",
        "mafft-align",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime, workspace = context.runtime, context.workspace
        del workspace
        config = spec.family
        if not isinstance(config, ProteinBridgeFamilySpec):
            raise TypeError("invalid protein bridge family spec")
        rng = random.Random(spec.seed)
        anchor_a = runtime.generate_sequences("protein", 1, config.sequence_length, spec.seed)[0]
        divergent = rng.sample(range(config.sequence_length), round(config.sequence_length * config.anchor_divergence))
        masked_anchor = "".join("_" if index in divergent else residue for index, residue in enumerate(anchor_a))
        anchor_b = runtime.run_tool(
            "random-protein-sample",
            {"sequences": [masked_anchor]},
            {"codon_scheme": "UNIFORM", "seed": spec.seed + 1},
        )["results"][0]["sequence"]

        masked_candidates = []
        for candidate_index in range(config.num_candidates):
            fraction_b = (candidate_index + 1) / (config.num_candidates + 1)
            from_b = set(rng.sample(divergent, round(len(divergent) * fraction_b)))
            candidate = [
                anchor_b[index] if index in from_b else anchor_a[index] for index in range(config.sequence_length)
            ]
            noise = rng.sample(range(config.sequence_length), round(config.sequence_length * config.candidate_noise))
            for index in noise:
                candidate[index] = "_"
            masked_candidates.append("".join(candidate))
        sampled = runtime.run_tool(
            "random-protein-sample",
            {"sequences": masked_candidates},
            {"codon_scheme": "UNIFORM", "seed": spec.seed + 2},
        )
        candidates = [item["sequence"] for item in sampled["results"]]

        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [anchor_a, anchor_b, *candidates]},
            {"num_recycles": 4, "max_batch_residues": 1200},
        )["structures"]
        if len(predicted) != config.num_candidates + 2:
            raise RuntimeError("ESMFold returned the wrong number of structures")
        structures = [_structure_text(item) for item in predicted]
        quality = runtime.run_tool("structure-metrics", {"structures": structures}, {})["metrics"]
        radii = [float(item["gyration_radius"]) for item in quality]
        radius_midpoint = (radii[0] + radii[1]) / 2

        raw_ids = [f"bridge_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        tm_scores: dict[str, dict[str, float]] = {}
        triage_scores: dict[str, float] = {}
        for raw_id, structure, radius in zip(raw_ids, structures[2:], radii[2:], strict=True):
            scores = []
            for anchor in structures[:2]:
                aligned = runtime.run_tool(
                    "tmalign-alignment",
                    {"query_structure": structure, "reference_structure": anchor},
                    {},
                )
                scores.append(float(aligned["metrics"]["tm_score_chain_2"]))
            sample = mapping[raw_id]
            tm_scores[sample] = {"anchor_a": scores[0], "anchor_b": scores[1]}
            triage_scores[sample] = 0.85 * min(scores) + 0.15 / (1 + abs(radius - radius_midpoint))

        shortlist = sorted(triage_scores, key=lambda sample: (-triage_scores[sample], sample))[: config.shortlist_size]
        sequence_by_sample = {mapping[raw]: sequence for raw, sequence in zip(raw_ids, candidates, strict=True)}
        alignment_ids = ["Anchor_A", "Anchor_B", *shortlist]
        alignment = runtime.run_tool(
            "mafft-align",
            {
                "sequences": [anchor_a, anchor_b, *(sequence_by_sample[sample] for sample in shortlist)],
                "sequence_ids": alignment_ids,
            },
            {"align_method": "auto", "max_iterations": 0, "threads": 1},
        )["msa"]
        aligned = dict(zip(alignment["sequence_ids"], alignment["aligned_sequences"], strict=True))
        identity_scores = {
            sample: min(
                _aligned_identity(aligned[sample], aligned["Anchor_A"]),
                _aligned_identity(aligned[sample], aligned["Anchor_B"]),
            )
            for sample in shortlist
        }
        final_scores = {sample: 0.9 * triage_scores[sample] + 0.1 * identity_scores[sample] for sample in shortlist}
        ranking = sorted(shortlist, key=lambda sample: (-final_scores[sample], sample))
        gaps = [final_scores[left] - final_scores[right] for left, right in pairwise(ranking)]
        if gaps and min(gaps) < config.min_score_gap:
            raise RuntimeError("final bridge ranking has insufficient score separation")

        public_files = {
            "data/proteins.fasta": fasta(
                [
                    ("Anchor_A", anchor_a),
                    ("Anchor_B", anchor_b),
                    *sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, candidates, strict=True)),
                ]
            )
        }
        rubric = (
            "Credit requires the exact four-member structural shortlist and its complete final ranking: "
            + ", ".join(sorted(shortlist))
            + "; "
            + " > ".join(ranking)
        )
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "anchor_sequences": {"Anchor_A": anchor_a, "Anchor_B": anchor_b},
                    "candidate_sequences": dict(zip(raw_ids, candidates, strict=True)),
                    "gyration_radii": dict(zip(["Anchor_A", "Anchor_B", *mapping.values()], radii, strict=True)),
                    "tm_scores": tm_scores,
                    "triage_scores": triage_scores,
                    "shortlist": shortlist,
                    "identity_scores": identity_scores,
                    "final_scores": final_scores,
                    "ranking": ranking,
                },
                anonymization_map=mapping,
                evidence={
                    "structure_sha256": [hashlib.sha256(item.encode()).hexdigest() for item in structures],
                    "prediction_config": {"num_recycles": 4, "max_batch_residues": 1200},
                    "alignment_config": {"align_method": "auto", "max_iterations": 0, "threads": 1},
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    SetAssertion(field="shortlist", expected=shortlist),
                    RankingAssertion(field="bridge_ranking", expected=ranking),
                ],
                rubric_text=rubric,
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Find and rank proteins that structurally bridge two anchor folds",
                public_files=["data/proteins.fasta"],
                answer_format="shortlist: Sample_..., ...\nranking: Sample_... > Sample_... > ...",
                default_question=(
                    "Use only `data/proteins.fasta` and the following pipeline. Predict all structures with "
                    "`esmfold-prediction` using `num_recycles=4` and `max_batch_residues=1200`. Run "
                    "`structure-metrics` on those predictions. For every candidate, run TM-align twice with the "
                    "candidate as query and each anchor as reference; use `tm_score_chain_2`. Let R be its gyration "
                    "radius and R0 the mean anchor radius. Compute T = 0.85*min(TM_A, TM_B) + "
                    "0.15/(1+abs(R-R0)). Retain the four highest-T candidates, breaking exact ties by sample ID. "
                    "Run MAFFT on the two anchors and these four candidates with `align_method=auto`, "
                    "`max_iterations=0`, and one thread. For each finalist, calculate ungapped pairwise identity to "
                    "each anchor (exclude columns containing a gap in either member), and let I be the smaller "
                    "identity. Compute F = 0.9*T + 0.1*I and rank all four by descending F, again breaking exact "
                    "ties by sample ID. Report both the unordered shortlist and complete final ranking."
                ),
            ),
        )


PROTEIN_BRIDGE_FAMILY = ProteinBridgeFamily()
