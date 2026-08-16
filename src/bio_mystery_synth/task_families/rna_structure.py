"""RNA secondary-structure ranking family."""

from __future__ import annotations

import random

from bio_mystery_synth.biology import base_pairs, fasta, jaccard
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
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import RNAStructureFamilySpec


@register
class RNAStructureFamily:
    family_id = "rna-structure-ranking"
    config_model = RNAStructureFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_candidates=5, sequence_length=80),
        Difficulty.MEDIUM: dict(num_candidates=8, sequence_length=120),
        Difficulty.HARD: dict(num_candidates=48, sequence_length=600),
    }
    tools = ("random-nucleotide-sample", "viennarna-prediction")
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime, workspace = context.runtime, context.workspace
        del workspace
        config = spec.family
        if not isinstance(config, RNAStructureFamilySpec):
            raise TypeError("invalid RNA structure family spec")
        rng = random.Random(spec.seed)
        reference = runtime.generate_sequences("rna", 1, config.sequence_length, spec.seed)[0].replace("T", "U")
        mutation_counts = config.mutation_counts or [
            max(1, round(config.sequence_length * (index + 1) / (config.num_candidates * 3)))
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
            "random-nucleotide-sample",
            {"sequences": masked},
            {"sequence_type": "rna", "substitution_scheme": "N", "seed": spec.seed + 1},
        )
        candidates = [item["sequence"].replace("T", "U") for item in sampled["results"]]
        folded = runtime.run_tool(
            "viennarna-prediction",
            {"sequences": [reference, *candidates]},
            {"temperature": config.temperature},
        )["results"]
        structures = [item["structure"] for item in folded]
        if any(structure is None for structure in structures):
            raise RuntimeError("ViennaRNA returned an empty structure")
        reference_pairs = base_pairs(structures[0])
        raw_ids = [f"rna_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        scores = {
            mapping[raw]: jaccard(reference_pairs, base_pairs(structure))
            for raw, structure in zip(raw_ids, structures[1:], strict=True)
        }
        ranking = sorted(scores, key=lambda sample: (-scores[sample], sample))
        if len(ranking) > 1 and scores[ranking[0]] - scores[ranking[1]] < config.min_score_gap:
            raise RuntimeError("RNA ranking has no unique winner at the configured score gap")
        records = [
            ("Reference", reference),
            *sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, candidates, strict=True)),
        ]
        public_files = {"data/sequences.fasta": fasta(records)}
        rubric = "Credit requires this complete descending base-pair Jaccard ranking: " + " > ".join(ranking)
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.DETERMINISTIC,
                facts={
                    "reference_sequence": reference,
                    "candidate_sequences": dict(zip(raw_ids, candidates, strict=True)),
                    "structures": dict(zip(["reference", *raw_ids], structures, strict=True)),
                    "scores": scores,
                    "ranking": ranking,
                },
                anonymization_map=mapping,
                evidence={"tool": "viennarna-prediction", "temperature": config.temperature},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.DETERMINISTIC,
                assertions=[RankingAssertion(field="structure_similarity", expected=ranking)],
                rubric_text=rubric,
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Rank RNA candidates by secondary-structure similarity",
                public_files=sorted(public_files),
                answer_format="A single descending ranking: Sample_A > Sample_B > ...",
                default_question=(
                    f"Fold every sequence in `data/sequences.fasta` with ViennaRNA at {config.temperature:g} °C. "
                    "Compare each candidate with `Reference` using Jaccard similarity of 0-based base-pair sets and "
                    "report the complete descending ranking."
                ),
            ),
        )


RNA_STRUCTURE_FAMILY = RNAStructureFamily()
