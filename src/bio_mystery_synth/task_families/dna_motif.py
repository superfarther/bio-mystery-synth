"""DNA motif localization family."""

from __future__ import annotations

import random

from bio_mystery_synth.biology import fasta, reverse_complement
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
from bio_mystery_synth.task_families.specs import DNAMotifFamilySpec


def _meme(motif: str) -> str:
    rows = []
    for base in motif:
        rows.append(" ".join("0.97" if candidate == base else "0.01" for candidate in "ACGT"))
    matrix = "\n".join(rows)
    return (
        "MEME version 4\n\nALPHABET= ACGT\n\nstrands: + -\n\n"
        "Background letter frequencies\nA 0.25 C 0.25 G 0.25 T 0.25\n\n"
        f"MOTIF SYNTHETIC_MOTIF\nletter-probability matrix: alength= 4 w= {len(motif)} nsites= 20 E= 0\n"
        f"{matrix}\n"
    )


def _replace_exact(sequence: str, motif: str) -> str:
    alternatives = (motif, reverse_complement(motif))
    for pattern in alternatives:
        start = sequence.find(pattern)
        while start >= 0:
            replacement = "A" if sequence[start] != "A" else "C"
            sequence = sequence[:start] + replacement + sequence[start + 1 :]
            start = sequence.find(pattern)
    return sequence


@register
class DNAMotifFamily:
    family_id = "dna-motif-localization"
    config_model = DNAMotifFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_sequences=8, sequence_length=500, num_targets=1, num_decoys=2),
        Difficulty.MEDIUM: dict(num_sequences=16, sequence_length=1000, num_targets=2, num_decoys=3),
        Difficulty.HARD: dict(num_sequences=96, sequence_length=20_000, num_targets=8, num_decoys=24),
    }
    tools = ("random-nucleotide-sample", "meme-fimo-scan")
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime, workspace = context.runtime, context.workspace
        config = spec.family
        if not isinstance(config, DNAMotifFamilySpec):
            raise TypeError("invalid DNA motif family spec")
        rng = random.Random(spec.seed)
        sequences = runtime.generate_sequences(
            "dna", config.num_sequences, config.sequence_length, spec.seed, config.gc_fraction
        )
        sequences = [_replace_exact(sequence.upper(), config.motif) for sequence in sequences]
        raw_ids = [f"dna_{index:03d}" for index in range(1, config.num_sequences + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        order = list(range(config.num_sequences))
        rng.shuffle(order)
        target_indices = order[: config.num_targets]
        decoy_indices = order[config.num_targets : config.num_targets + config.num_decoys]
        injected: list[dict[str, str | int]] = []
        for index in target_indices:
            start = rng.randrange(0, config.sequence_length - len(config.motif) + 1)
            strand = rng.choice(["+", "-"])
            inserted = config.motif if strand == "+" else reverse_complement(config.motif)
            sequences[index] = sequences[index][:start] + inserted + sequences[index][start + len(inserted) :]
            injected.append(
                {
                    "sample": mapping[raw_ids[index]],
                    "start": start + 1,
                    "end": start + len(inserted),
                    "strand": strand,
                }
            )
        for index in decoy_indices:
            decoy = list(config.motif)
            position = rng.randrange(len(decoy))
            decoy[position] = rng.choice([base for base in "ACGT" if base != decoy[position]])
            start = rng.randrange(0, config.sequence_length - len(decoy) + 1)
            sequences[index] = sequences[index][:start] + "".join(decoy) + sequences[index][start + len(decoy) :]

        motif_text = _meme(config.motif)
        motif_path = workspace / "motif.meme"
        motif_path.write_text(motif_text)
        fimo = runtime.run_tool(
            "meme-fimo-scan",
            {"sequences": sequences, "motifs": str(motif_path)},
            {"threshold": config.fimo_threshold, "both_strands": True},
        )
        records = sorted(((mapping[raw], sequence) for raw, sequence in zip(raw_ids, sequences, strict=True)))
        expected = sorted(f"{item['sample']}:{item['start']}-{item['end']}:{item['strand']}" for item in injected)
        rubric = "Credit requires exactly these sample, 1-based interval, and strand tuples: " + ", ".join(expected)
        answer = AnswerSpec(
            oracle_type=OracleType.INJECTED,
            assertions=[SetAssertion(field="motif_hits", expected=expected)],
            rubric_text=rubric,
        )
        public_files = {
            "data/sequences.fasta": fasta(records),
            "data/motif.meme": motif_text,
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.INJECTED,
                facts={
                    "motif": config.motif,
                    "injected_hits": injected,
                    "raw_sequences": dict(zip(raw_ids, sequences, strict=True)),
                },
                anonymization_map=mapping,
                evidence={"fimo": fimo},
            ),
            answer=answer,
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Locate the synthetic DNA motif",
                public_files=sorted(public_files),
                answer_format="One tuple per line: Sample_ID:start-end:strand, using 1-based inclusive coordinates.",
                default_question=(
                    "Scan `data/sequences.fasta` with the PWM in `data/motif.meme`. Identify every sequence carrying "
                    "the synthetic motif and report its 1-based inclusive interval and strand. Report only motif hits."
                ),
            ),
        )


DNA_MOTIF_FAMILY = DNAMotifFamily()
