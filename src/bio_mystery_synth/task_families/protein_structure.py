"""Protein structure nearest-neighbor family."""

from __future__ import annotations

import random
from pathlib import Path

from bio_mystery_synth.models import (
    AnswerSpec,
    FamilyResult,
    GroundTruth,
    OracleType,
    ProteinStructureFamilySpec,
    QuestionContext,
    RankingAssertion,
    ScenarioSpec,
)
from bio_mystery_synth.runtime import Runtime
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.utils import anonymize, fasta


def _structure_payload(structure: dict[str, object]) -> tuple[str, str]:
    content = structure.get("structure")
    if not isinstance(content, str):
        raise RuntimeError("structure predictor returned no structure text")
    format_name = str(structure.get("structure_format") or "pdb").lower()
    extension = "cif" if "cif" in format_name else "pdb"
    return content, extension


@register
class ProteinStructureFamily:
    family_id = "protein-structure-nearest"

    def generate(self, spec: ScenarioSpec, runtime: Runtime, workspace: Path) -> FamilyResult:
        del workspace
        config = spec.family
        if not isinstance(config, ProteinStructureFamilySpec):
            raise TypeError("invalid protein structure family spec")
        rng = random.Random(spec.seed)
        reference = runtime.generate_sequences("protein", 1, config.sequence_length, spec.seed)[0]
        mutation_counts = config.mutation_counts or [
            max(1, round(config.sequence_length * (index + 1) / (config.num_candidates * 2)))
            for index in range(config.num_candidates)
        ]
        masked = []
        for count in mutation_counts:
            positions = rng.sample(range(config.sequence_length), min(count, config.sequence_length))
            candidate = list(reference)
            for position in positions:
                candidate[position] = "_"
            masked.append("".join(candidate))
        sampled = runtime.run_tool(
            "random-protein-sample",
            {"sequences": masked},
            {"codon_scheme": "UNIFORM", "seed": spec.seed + 1},
        )
        candidates = [item["sequence"] for item in sampled["results"]]
        predicted = runtime.run_tool(
            config.prediction_tool,
            {"complexes": [reference, *candidates]},
            {},
        )["structures"]
        if len(predicted) != config.num_candidates + 1:
            raise RuntimeError("structure predictor returned the wrong number of structures")
        structure_data = [_structure_payload(item) for item in predicted]
        reference_structure = structure_data[0][0]
        scores = []
        for candidate_structure, _ in structure_data[1:]:
            result = runtime.run_tool(
                config.alignment_tool,
                {"query_structure": candidate_structure, "reference_structure": reference_structure},
                {},
            )
            scores.append(float(result["metrics"]["tm_score_chain_2"]))
        raw_ids = [f"protein_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        score_map = {mapping[raw]: score for raw, score in zip(raw_ids, scores, strict=True)}
        ranking = sorted(score_map, key=lambda sample: (-score_map[sample], sample))
        if len(ranking) > 1 and score_map[ranking[0]] - score_map[ranking[1]] < config.min_score_gap:
            raise RuntimeError("protein ranking has no unique winner at the configured score gap")
        public_files: dict[str, str] = {
            "data/sequences.fasta": fasta(
                [
                    ("Reference", reference),
                    *sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, candidates, strict=True)),
                ]
            )
        }
        reference_content, reference_ext = structure_data[0]
        public_files[f"data/reference.{reference_ext}"] = reference_content
        for raw, (content, extension) in zip(raw_ids, structure_data[1:], strict=True):
            path = f"data/candidates/{mapping[raw]}.{extension}"
            public_files[path] = content
        rubric = "Credit requires this complete descending reference-normalized TM-score ranking: " + " > ".join(
            ranking
        )
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "reference_sequence": reference,
                    "candidate_sequences": dict(zip(raw_ids, candidates, strict=True)),
                    "tm_scores": score_map,
                    "ranking": ranking,
                },
                anonymization_map=mapping,
                evidence={
                    "prediction_tool": config.prediction_tool,
                    "alignment_tool": config.alignment_tool,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[RankingAssertion(field="structure_similarity", expected=ranking)],
                rubric_text=rubric,
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Rank protein candidates by structural similarity",
                public_files=sorted(public_files),
                answer_format="A single descending ranking: Sample_A > Sample_B > ...",
                default_question=(
                    f"Align each file under `data/candidates/` to `data/reference.{reference_ext}` with TM-align. "
                    "Use the TM-score normalized by the reference length and report the complete descending ranking."
                ),
            ),
        )


PROTEIN_STRUCTURE_FAMILY = ProteinStructureFamily()
