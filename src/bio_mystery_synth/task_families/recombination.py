"""Windowed phylogenetic recombination family."""

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
    ScenarioSpec,
    SetAssertion,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import RecombinationFamilySpec


def _mutate(sequence: str, count: int, rng: random.Random) -> str:
    chars = list(sequence)
    for position in rng.sample(range(len(chars)), count):
        chars[position] = rng.choice([base for base in "ACGT" if base != chars[position]])
    return "".join(chars)


def _assign_windows(sequence: str, reference_a: str, reference_b: str, size: int) -> list[str]:
    assignments = []
    for start in range(0, len(sequence), size):
        window = sequence[start : start + size]
        distance_a = sum(left != right for left, right in zip(window, reference_a[start : start + size], strict=True))
        distance_b = sum(left != right for left, right in zip(window, reference_b[start : start + size], strict=True))
        assignments.append("A" if distance_a < distance_b else "B" if distance_b < distance_a else "tie")
    return assignments


@register
class RecombinationFamily:
    family_id = "windowed-recombination"
    config_model = RecombinationFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_candidates=12, sequence_length=1000, num_recombinants=1, window_size=100),
        Difficulty.MEDIUM: dict(num_candidates=48, sequence_length=4000, num_recombinants=3, window_size=200),
        Difficulty.HARD: dict(num_candidates=96, sequence_length=8000, num_recombinants=5, window_size=250),
    }
    tools = ("mafft-align",)
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime, workspace = context.runtime, context.workspace
        del workspace
        config = spec.family
        if not isinstance(config, RecombinationFamilySpec):
            raise TypeError("invalid recombination family spec")
        rng = random.Random(spec.seed)
        ancestor = runtime.generate_sequences("dna", 1, config.sequence_length, spec.seed, 0.5)[0]
        divergence = round(config.sequence_length * config.clade_divergence)
        reference_a = _mutate(ancestor, divergence, rng)
        reference_b = _mutate(ancestor, divergence, rng)
        within = round(config.sequence_length * config.within_clade_divergence)
        normal_count = config.num_candidates - config.num_recombinants
        candidates = [
            _mutate(reference_a if index % 2 == 0 else reference_b, within, rng)
            for index in range(normal_count)
        ]
        for _ in range(config.num_recombinants):
            window = rng.randrange(1, config.sequence_length // config.window_size - 1)
            breakpoint = window * config.window_size
            recombinant = reference_a[:breakpoint] + reference_b[breakpoint:]
            candidates.append(_mutate(recombinant, within, rng))
        order = list(range(config.num_candidates))
        rng.shuffle(order)
        candidates = [candidates[index] for index in order]
        raw_ids = [f"isolate_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        expected = []
        assignments = {}
        for raw, sequence in zip(raw_ids, candidates, strict=True):
            label = mapping[raw]
            windows = _assign_windows(sequence, reference_a, reference_b, config.window_size)
            assignments[label] = windows
            changes = [index for index in range(1, len(windows)) if windows[index] != windows[index - 1]]
            switches = [index for index in changes if windows[index - 1 : index + 1] == ["A", "B"]]
            if changes == switches and len(switches) == 1:
                expected.append(f"{label}:{switches[0] * config.window_size + 1}")
        alignment = runtime.run_tool(
            "mafft-align",
            {"sequences": [reference_a, reference_b, *candidates], "sequence_ids": ["Clade_A", "Clade_B", *raw_ids]},
            {"align_method": "auto", "max_iterations": 0, "threads": 4},
        )
        expected.sort()
        public_files = {
            "data/isolates.fasta": fasta(
                [
                    ("Clade_A_Reference", reference_a),
                    ("Clade_B_Reference", reference_b),
                    *sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, candidates, strict=True)),
                ]
            )
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.DETERMINISTIC,
                facts={
                    "ancestor": ancestor,
                    "reference_a": reference_a,
                    "reference_b": reference_b,
                    "raw_candidates": dict(zip(raw_ids, candidates, strict=True)),
                    "window_assignments": assignments,
                    "recombinants": expected,
                },
                anonymization_map=mapping,
                evidence={"alignment_metadata": alignment.get("metadata", {}), "tool": "mafft-align"},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.DETERMINISTIC,
                assertions=[SetAssertion(field="recombination_switches", expected=expected)],
                rubric_text="Credit requires exactly these recombinant and switch coordinates: " + ", ".join(expected),
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Detect mosaic isolates by windowed phylogenetic assignment",
                public_files=sorted(public_files),
                answer_format="One line per recombinant: Sample_ID:first_coordinate_of_B_window.",
                default_question=(
                    "Align all records in `data/isolates.fasta` with MAFFT. Remove columns containing a gap in either "
                    f"reference, split the remaining alignment into consecutive {config.window_size}-nt windows, and "
                    "assign each sample window to the reference with lower Hamming distance; ties remain unassigned. "
                    "Report samples with exactly one A-to-B switch and the 1-based first coordinate of the first "
                    "B-assigned window."
                ),
            ),
        )


RECOMBINATION_FAMILY = RecombinationFamily()
