"""CRISPR spacer to phage linkage family."""

from __future__ import annotations

import random
from pathlib import Path

from bio_mystery_synth.models import (
    AnswerSpec,
    CrisprLinkageFamilySpec,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    ScenarioSpec,
    SetAssertion,
)
from bio_mystery_synth.runtime import Runtime
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.utils import anonymize, fasta, reverse_complement


def _random_dna(rng: random.Random, length: int) -> str:
    return "".join(rng.choice("ACGT") for _ in range(length))


@register
class CrisprLinkageFamily:
    family_id = "crispr-spacer-linkage"

    def generate(self, spec: ScenarioSpec, runtime: Runtime, workspace: Path) -> FamilyResult:
        del workspace
        config = spec.family
        if not isinstance(config, CrisprLinkageFamilySpec):
            raise TypeError("invalid CRISPR linkage family spec")
        rng = random.Random(spec.seed)
        genomes = runtime.generate_sequences("dna", config.num_genomes, config.genome_length, spec.seed, 0.5)
        phages = runtime.generate_sequences("dna", config.num_phages, config.phage_length, spec.seed + 1, 0.5)
        raw_ids = [f"host_{index:03d}" for index in range(1, config.num_genomes + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        chosen = rng.sample(range(config.num_genomes), config.num_targets + config.num_decoys)
        targets = set(chosen[: config.num_targets])
        injected = []
        for index in chosen:
            spacers = [_random_dna(rng, config.spacer_length) for _ in range(config.num_repeats - 1)]
            linked_phages: set[int] = set()
            if index in targets:
                for spacer_index in range(config.linked_spacers):
                    phage_index = spacer_index % config.num_phages
                    start = rng.randrange(config.phage_length - config.spacer_length + 1)
                    spacer = phages[phage_index][start : start + config.spacer_length]
                    spacers[spacer_index] = spacer if rng.choice([True, False]) else reverse_complement(spacer)
                    linked_phages.add(phage_index)
            array = config.repeat + "".join(spacer + config.repeat for spacer in spacers)
            start = rng.randrange(config.genome_length - len(array) + 1)
            genomes[index] = genomes[index][:start] + array + genomes[index][start + len(array) :]
            if index in targets:
                injected.append(
                    {
                        "sample": mapping[raw_ids[index]],
                        "start": start + 1,
                        "end": start + len(array),
                        "phages": [f"Phage_{phage_index + 1:02d}" for phage_index in sorted(linked_phages)],
                    }
                )
        detection = runtime.run_tool(
            "minced-crispr",
            {"sequences": genomes},
            {
                "min_num_repeats": config.num_repeats,
                "min_repeat_length": len(config.repeat),
                "max_repeat_length": len(config.repeat),
                "min_spacer_length": config.spacer_length,
                "max_spacer_length": config.spacer_length,
            },
        )
        expected = sorted(
            f"{item['sample']}:{item['start']}-{item['end']}:{','.join(item['phages'])}" for item in injected
        )
        public_files = {
            "data/host_genomes.fasta": fasta(
                sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, genomes, strict=True))
            ),
            "data/challenge_phages.fasta": fasta(
                [(f"Phage_{index + 1:02d}", sequence) for index, sequence in enumerate(phages)]
            ),
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.INJECTED,
                facts={
                    "repeat": config.repeat,
                    "linked_arrays": injected,
                    "raw_genomes": dict(zip(raw_ids, genomes, strict=True)),
                    "phages": {f"Phage_{index + 1:02d}": sequence for index, sequence in enumerate(phages)},
                },
                anonymization_map=mapping,
                evidence={"minced": detection},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.INJECTED,
                assertions=[SetAssertion(field="linked_crispr_arrays", expected=expected)],
                rubric_text="Credit requires exactly these linked arrays: " + "; ".join(expected),
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Link CRISPR arrays to synthetic challenge phages",
                public_files=sorted(public_files),
                answer_format="One line per retained array: Sample_ID:start-end:comma-separated_Phage_IDs.",
                default_question=(
                    f"Run MinCED on `data/host_genomes.fasta` using exactly {config.num_repeats} repeats, repeat "
                    f"length {len(config.repeat)}, and spacer length {config.spacer_length}. For every detected array, "
                    "match each spacer exactly against either strand of `data/challenge_phages.fasta`. Retain arrays "
                    f"with at least {config.linked_spacers} matching spacers and report the 1-based inclusive array "
                    "interval plus every uniquely linked phage in lexical order."
                ),
            ),
        )


CRISPR_LINKAGE_FAMILY = CrisprLinkageFamily()
