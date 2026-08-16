"""Promoter, gene-boundary, and homology evidence fusion."""

from __future__ import annotations

import random

from bio_mystery_synth.biology import CODONS, fasta, reverse_complement
from bio_mystery_synth.core import (
    AnswerSpec,
    Difficulty,
    ExactAssertion,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    ScenarioSpec,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import PromoterCassetteFamilySpec

_PROMOTER = "AAAATTGTGAGCGGATAACAATTTCACACAGGAAACAGCTATGACC"
_AA = "ACDEFGHIKLMNPQRSTVWY"


def _mutate(sequence: str, count: int, rng: random.Random) -> str:
    chars = list(sequence)
    for position in rng.sample(range(1, len(chars)), count):
        chars[position] = rng.choice(_AA.replace(chars[position], ""))
    return "".join(chars)


def _gene(protein: str) -> str:
    return "AGGAGGAAAA" + "".join(CODONS[aa] for aa in protein) + "TAA"


@register
class PromoterCassetteFamily:
    family_id = "promoter-cassette-forensics"
    config_model = PromoterCassetteFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_cassettes=8, cassette_length=2200, protein_length=90, num_homologs=4),
        Difficulty.MEDIUM: dict(num_cassettes=12, cassette_length=2800, protein_length=110, num_homologs=5),
        Difficulty.HARD: dict(num_cassettes=18, cassette_length=3600, protein_length=150, num_homologs=7),
    }
    tools = (
        "prodigal-prediction",
        "pyhmmer-jackhmmer",
        "pyhmmer-nhmmer",
        "promoter-calculator",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, PromoterCassetteFamilySpec):
            raise TypeError("invalid promoter cassette family spec")
        rng = random.Random(spec.seed)
        marker = "M" + runtime.generate_sequences("protein", 1, config.protein_length, spec.seed)[0][1:]
        homologs = [_mutate(marker, 5 + 4 * index, rng) for index in range(config.num_homologs)]
        homologs[-2] = homologs[-2][: len(homologs[-2]) // 2]
        homologs[-1] = homologs[-1][: len(homologs[-1]) // 2] + "G" * (len(homologs[-1]) // 2)
        cassettes = runtime.generate_sequences("dna", config.num_cassettes, config.cassette_length, spec.seed + 1, 0.5)
        gene_start = config.cassette_length // 2
        promoter_start = gene_start - 115
        for index, protein in enumerate(homologs):
            gene = _gene(protein)
            cassettes[index] = cassettes[index][:gene_start] + gene + cassettes[index][gene_start + len(gene) :]
            if index < config.num_homologs - 2:
                promoter = list(_PROMOTER)
                for position in rng.sample(range(len(promoter)), min(index * 2, 12)):
                    promoter[position] = rng.choice("ACGT".replace(promoter[position], ""))
                promoter_text = "".join(promoter)
                if index == config.num_homologs - 3:
                    promoter_text = reverse_complement(promoter_text)
                cassettes[index] = (
                    cassettes[index][:promoter_start]
                    + promoter_text
                    + cassettes[index][promoter_start + len(promoter_text) :]
                )

        raw_ids = [f"cassette_{index:03d}" for index in range(1, config.num_cassettes + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        gene_calls = runtime.run_tool(
            "prodigal-prediction",
            {"input_sequences": cassettes},
            {"meta_mode": True, "closed_ends": False, "min_gene": 90, "num_threads": 4},
        )
        called: dict[int, dict[str, object]] = {}
        for index, protein in enumerate(homologs):
            matches = [
                orf
                for orf in gene_calls["results"][index]["orfs"]
                if orf["strand"] == "+" and orf["amino_acid_sequence"] == protein
            ]
            if len(matches) == 1:
                called[index] = matches[0]
        full_indexes = [index for index in called if len(homologs[index]) == config.protein_length]
        if len(full_indexes) < 2:
            raise RuntimeError("gene calling left fewer than two intact homologs")

        jackhmmer = runtime.run_tool(
            "pyhmmer-jackhmmer",
            {"sequences": [marker], "target_sequences": homologs},
            {
                "max_iterations": 4,
                "evalue_threshold": 1e-3,
                "domain_evalue_threshold": 1e-3,
                "inclusion_evalue_threshold": 1e-3,
                "inclusion_domain_evalue_threshold": 1e-3,
                "num_threads": 4,
            },
        )
        nucleotide_marker = "".join(CODONS[aa] for aa in marker)
        nhmmer = runtime.run_tool(
            "pyhmmer-nhmmer",
            {"sequences": [nucleotide_marker], "target_sequences": cassettes},
            {"strand": "both", "evalue_threshold": 1e-3, "domain_evalue_threshold": 1e-3, "num_threads": 4},
        )
        window_starts = {index: max(0, int(called[index]["nucleotide_start"]) - 241) for index in full_indexes}
        promoter_windows = [
            cassettes[index][window_starts[index] : int(called[index]["nucleotide_start"]) + 19]
            for index in full_indexes
        ]
        promoters = runtime.run_tool(
            "promoter-calculator",
            {"sequences": promoter_windows},
            {"threads": 4, "circular": False},
        )
        candidates: dict[int, dict[str, object]] = {}
        for result_index, index in enumerate(full_indexes):
            coding_start = int(called[index]["nucleotide_start"])
            upstream = [
                {**prediction, "global_tss": window_starts[index] + int(prediction["tss"])}
                for prediction in promoters["results"][result_index]["predictions"]
                if prediction["strand"] == "+"
                and 0 < coding_start - (window_starts[index] + int(prediction["tss"]) + 1) <= 180
            ]
            if upstream:
                candidates[index] = max(upstream, key=lambda prediction: float(prediction["Tx_rate"]))
        if len(candidates) < 2:
            raise RuntimeError("promoter analysis left fewer than two intact candidates")
        winner = max(candidates, key=lambda index: (float(candidates[index]["Tx_rate"]), -index))
        winner_id = mapping[raw_ids[winner]]
        winner_orf = called[winner]
        winner_tss = int(candidates[winner]["global_tss"]) + 1
        interval = f"{winner_orf['nucleotide_start']}-{winner_orf['nucleotide_end']}"

        public_files = {
            "data/cassettes.fasta": fasta(
                sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, cassettes, strict=True))
            ),
            "data/family_marker.fasta": fasta([("Synthetic_family_marker", marker)]),
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "raw_cassettes": dict(zip(raw_ids, cassettes, strict=True)),
                    "injected_homologs": dict(zip(raw_ids[: len(homologs)], homologs, strict=True)),
                    "called_orfs": {mapping[raw_ids[index]]: value for index, value in called.items()},
                    "upstream_promoters": {mapping[raw_ids[index]]: value for index, value in candidates.items()},
                    "winner": winner_id,
                    "winner_tss": winner_tss,
                    "winner_interval": interval,
                },
                anonymization_map=mapping,
                evidence={
                    "gene_calls": gene_calls,
                    "iterative_homology": jackhmmer,
                    "nucleotide_homology": nhmmer,
                    "promoters": promoters,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    ExactAssertion(field="sample", expected=winner_id),
                    ExactAssertion(field="tss", expected=winner_tss),
                    ExactAssertion(field="orf_interval", expected=interval),
                ],
                rubric_text=f"Credit requires {winner_id}, TSS {winner_tss}, and ORF interval {interval}.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Resolve the expressed intact member of a divergent synthetic cassette family",
                public_files=sorted(public_files),
                answer_format="sample: Sample_...\ntss: integer\norf_interval: start-end",
                default_question=(
                    "The anonymous DNA cassettes in `data/cassettes.fasta` contain unrelated background, partial "
                    "relatives, strand decoys, and several divergent members of the family represented by "
                    "`data/family_marker.fasta`. Identify the single cassette that combines a complete coding "
                    "region with the strongest plausible forward bacterial promoter immediately upstream. Report "
                    "the 1-based transcription start and the 1-based inclusive coding interval, including the "
                    "terminal stop codon. Sequence similarity, gene boundaries, strand, and promoter strength must "
                    "agree; no one signal is decisive by itself."
                ),
            ),
        )


PROMOTER_CASSETTE_FAMILY = PromoterCassetteFamily()
