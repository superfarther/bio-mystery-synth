"""Sequence-structure discordance cohort family."""

from __future__ import annotations

import random
import statistics

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
from bio_mystery_synth.task_families.advanced_protein import (
    aligned_identity,
    mutate,
    normalize,
    parse_fasta,
    structure_text,
)
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import StructuralDiscordanceFamilySpec


@register
class StructuralDiscordanceFamily:
    family_id = "structural-discordance-cohort"
    config_model = StructuralDiscordanceFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_candidates=16, sequence_length=160, shortlist_size=4),
        Difficulty.MEDIUM: dict(num_candidates=20, sequence_length=200, shortlist_size=5),
        Difficulty.HARD: dict(num_candidates=24, sequence_length=240, shortlist_size=6),
    }
    tools = (
        "esmfold-prediction",
        "mafft-align",
        "foldmason-msa",
        "foldmason-score-msa",
        "foldseek-cluster",
        "usalign-alignment",
        "dssp-secondary-structure",
        "pyrosetta-energy",
        "pyrosetta-sasa",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, StructuralDiscordanceFamilySpec):
            raise TypeError("invalid structural discordance family spec")
        rng = random.Random(spec.seed)
        anchor = "M" + runtime.generate_sequences("protein", 1, config.sequence_length, spec.seed)[0][1:]
        candidates = [
            mutate(anchor, round(config.sequence_length * (0.18 + 0.42 * index / (config.num_candidates - 1))), rng)
            for index in range(config.num_candidates)
        ]
        quarter = config.sequence_length // 4
        candidates[-3] = (
            candidates[-3][quarter : 3 * quarter] + candidates[-3][:quarter] + candidates[-3][3 * quarter :]
        )
        candidates[-2] = candidates[-2][: 2 * quarter] + "GPGPGPGPGPGP" + candidates[-2][2 * quarter + 12 :]
        candidates[-1] = candidates[-1][config.sequence_length // 2 :] + candidates[-1][: config.sequence_length // 2]
        raw_ids = [f"discordant_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        sample_ids = [mapping[raw] for raw in raw_ids]

        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [anchor, *candidates]},
            {"num_recycles": 6, "max_batch_residues": 1200, "seed": spec.seed},
        )["structures"]
        structures = [structure_text(item) for item in predicted]
        labels = ["Anchor", *[f"C{index:03d}" for index in range(1, config.num_candidates + 1)]]
        sequence_alignment = runtime.run_tool(
            "mafft-align",
            {"sequences": [anchor, *candidates], "sequence_ids": labels},
            {"align_method": "auto", "max_iterations": 100, "threads": 4},
        )["msa"]
        structural_alignment = runtime.run_tool(
            "foldmason-msa",
            {"structures": structures, "structure_ids": labels},
            {"search_mode": "local", "refine_iters": 2, "precluster": True, "num_threads": 8},
        )
        alignment_score = runtime.run_tool(
            "foldmason-score-msa",
            {"structures": structures, "structure_ids": labels, "msa": structural_alignment["aa_msa_fasta"]},
            {"num_threads": 8},
        )
        clusters = runtime.run_tool(
            "foldseek-cluster",
            {"structures": structures, "structure_ids": labels},
            {"cov": 0.7, "alignment_type": 1, "tmscore_threshold": 0.45, "num_threads": 8},
        )
        secondary = runtime.run_tool("dssp-secondary-structure", {"inputs": structures}, {})["results"]
        energies = runtime.run_tool("pyrosetta-energy", {"inputs": structures}, {})["results"]
        sasa = runtime.run_tool("pyrosetta-sasa", {"inputs": structures}, {})["results"]
        tm_scores = []
        for structure in structures[1:]:
            aligned = runtime.run_tool(
                "usalign-alignment",
                {"query_structure": structure, "reference_structure": structures[0]},
                {},
            )
            tm_scores.append(float(aligned["metrics"]["tm_score_structure_2"]))

        seq_records = dict(
            zip(sequence_alignment["sequence_ids"], sequence_alignment["aligned_sequences"], strict=True)
        )
        identities = [aligned_identity(seq_records[label], seq_records["Anchor"]) for label in labels[1:]]
        structure_records = parse_fasta(structural_alignment["aa_msa_fasta"])
        column_scores = [float(value) for value in alignment_score["column_scores"]]
        cutoff = statistics.median(column_scores)
        core_columns = [index for index, value in enumerate(column_scores) if value >= cutoff]
        gap_burden = [
            sum(structure_records[label][index] == "-" for index in core_columns) / len(core_columns)
            for label in labels[1:]
        ]
        discordance = [
            tm - identity - 0.25 * gaps for tm, identity, gaps in zip(tm_scores, identities, gap_burden, strict=True)
        ]
        shortlist_indexes = sorted(
            range(config.num_candidates), key=lambda index: (-discordance[index], sample_ids[index])
        )[: config.shortlist_size]
        energy_per_residue = [float(item["total_energy"]) / config.sequence_length for item in energies[1:]]
        sasa_per_residue = [float(item["total_sasa"]) / config.sequence_length for item in sasa[1:]]
        reference_ss = secondary[0]
        ss_similarity = [
            1
            - sum(
                abs(float(item[field]) - float(reference_ss[field])) for field in ("helix_pct", "sheet_pct", "loop_pct")
            )
            / 200
            for item in secondary[1:]
        ]
        confidence = [float(item["metrics"]["avg_plddt"]) for item in predicted[1:]]
        stability = list(
            zip(
                normalize(energy_per_residue, False),
                normalize(sasa_per_residue, False),
                normalize(confidence),
                normalize(ss_similarity),
                strict=True,
            )
        )
        final_scores = {
            sample_ids[index]: 0.35 * discordance[index]
            + 0.25 * stability[index][0]
            + 0.1 * stability[index][1]
            + 0.2 * stability[index][2]
            + 0.1 * stability[index][3]
            for index in shortlist_indexes
        }
        shortlist = [sample_ids[index] for index in shortlist_indexes]
        ranking = sorted(shortlist, key=lambda sample: (-final_scores[sample], sample))
        public_files = {
            "data/sequences.fasta": fasta([("Anchor", anchor), *sorted(zip(sample_ids, candidates, strict=True))]),
            "data/anchor.pdb": structures[0],
            **{
                f"data/cohort/{sample}.pdb": structure
                for sample, structure in zip(sample_ids, structures[1:], strict=True)
            },
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "candidate_sequences": dict(zip(raw_ids, candidates, strict=True)),
                    "sequence_identity": dict(zip(sample_ids, identities, strict=True)),
                    "structure_tm": dict(zip(sample_ids, tm_scores, strict=True)),
                    "core_gap_burden": dict(zip(sample_ids, gap_burden, strict=True)),
                    "discordance": dict(zip(sample_ids, discordance, strict=True)),
                    "energy_per_residue": dict(zip(sample_ids, energy_per_residue, strict=True)),
                    "sasa_per_residue": dict(zip(sample_ids, sasa_per_residue, strict=True)),
                    "secondary_similarity": dict(zip(sample_ids, ss_similarity, strict=True)),
                    "shortlist": shortlist,
                    "final_scores": final_scores,
                    "ranking": ranking,
                },
                anonymization_map=mapping,
                evidence={
                    "predictions": predicted,
                    "sequence_alignment": sequence_alignment,
                    "structural_alignment": structural_alignment,
                    "alignment_score": alignment_score,
                    "structure_clusters": clusters,
                    "secondary_structure": secondary,
                    "energies": energies,
                    "sasa": sasa,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    SetAssertion(field="discordant_shortlist", expected=shortlist),
                    RankingAssertion(field="stability_ranking", expected=ranking),
                ],
                rubric_text=(
                    "Credit requires shortlist "
                    + ", ".join(shortlist)
                    + " and stability ranking "
                    + " > ".join(ranking)
                ),
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Find stable structural mimics concealed by sequence divergence",
                public_files=sorted(public_files),
                answer_format=(
                    "shortlist: Sample_..., Sample_..., Sample_..., Sample_..., Sample_..., Sample_...\n"
                    "ranking: Sample_... > Sample_... > Sample_... > Sample_... > Sample_... > Sample_..."
                ),
                default_question=(
                    "The sequence and coordinate cohort under `data/` contains remote variants, rearranged decoys, "
                    "and true structural mimics of the anchor. Identify the six candidates with the strongest "
                    "positive disagreement between weak sequence similarity and retained three-dimensional topology, "
                    "while penalizing disruption of the cohort's conserved structural core. Rank those six by the "
                    "coherence of physical energy, solvent exposure, model confidence, and secondary-structure "
                    "composition. Report both the unordered six-member shortlist and its final stability ranking."
                ),
            ),
        )


STRUCTURAL_DISCORDANCE_FAMILY = StructuralDiscordanceFamily()
