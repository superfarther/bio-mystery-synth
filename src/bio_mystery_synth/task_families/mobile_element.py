"""Closed-world mobile-element host and boundary attribution."""

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
from bio_mystery_synth.task_families.specs import MobileElementFamilySpec


def _mutate_dna(sequence: str, fraction: float, rng: random.Random) -> str:
    chars = list(sequence)
    for position in rng.sample(range(len(chars)), round(len(chars) * fraction)):
        chars[position] = rng.choice("ACGT".replace(chars[position], ""))
    return "".join(chars)


def _gene(protein: str) -> str:
    return "AGGAGGAAAA" + "".join(CODONS[aa] for aa in protein) + "TAA"


@register
class MobileElementFamily:
    family_id = "mobile-element-attribution"
    config_model = MobileElementFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_genomes=12, genome_length=6000, element_length=1200),
        Difficulty.MEDIUM: dict(num_genomes=16, genome_length=8000, element_length=1250),
        Difficulty.HARD: dict(num_genomes=24, genome_length=12_000, element_length=1700),
    }
    tools = (
        "mmseqs2-search-genomes",
        "pyhmmer-nhmmer",
        "blast-create-db",
        "blast-search",
        "prodigal-prediction",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, MobileElementFamilySpec):
            raise TypeError("invalid mobile element family spec")
        rng = random.Random(spec.seed)
        genomes = runtime.generate_sequences("dna", config.num_genomes, config.genome_length, spec.seed, 0.5)
        parts = runtime.generate_sequences("dna", 4, 260, spec.seed + 1, 0.48)
        left, right, internal, filler_seed = parts
        left, right = left[:220], right[:220]
        internal = internal[:260]
        cargo = "M" + runtime.generate_sequences("protein", 1, 105, spec.seed + 2)[0][1:]
        gene = _gene(cargo)
        filler_length = config.element_length - len(left) - len(right) - len(internal) - len(gene)
        if filler_length < 120:
            raise RuntimeError("mobile element is too short for its evidence modules")
        filler = (filler_seed * (filler_length // len(filler_seed) + 1))[:filler_length]
        split = filler_length // 2
        element = left + filler[:split] + gene + filler[split:] + internal + right
        target_element = _mutate_dna(left, 0.06, rng) + element[len(left) : -len(right)] + _mutate_dna(right, 0.07, rng)
        interrupted = list(element)
        gene_offset = len(left) + split + 10
        stop = gene_offset + 3 * 45
        interrupted[stop : stop + 3] = "TAA"
        interrupted_element = reverse_complement("".join(interrupted))

        positions = [config.genome_length // 3 + index * 37 for index in range(5)]
        inserts = [
            target_element,
            interrupted_element,
            left + filler + internal,
            right + filler[: len(filler) // 2] + left + internal,
            _mutate_dna(internal, 0.12, rng),
        ]
        for index, insert in enumerate(inserts):
            start = positions[index]
            genomes[index] = genomes[index][:start] + insert + genomes[index][start + len(insert) :]

        raw_ids = [f"host_genome_{index:03d}" for index in range(1, config.num_genomes + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        sample_ids = [mapping[raw] for raw in raw_ids]
        coarse = runtime.run_tool(
            "mmseqs2-search-genomes",
            {"query_genomes": [left, internal, right]},
            {
                "target_genomes": genomes,
                "threads": 4,
                "sensitivity": 7.5,
                "evalue": 1e-3,
                "min_seq_id": 0.55,
                "coverage": 0.65,
                "cov_mode": 2,
                "strand": 2,
                "timeout": 240,
            },
        )
        nhmmer = runtime.run_tool(
            "pyhmmer-nhmmer",
            {"sequences": [internal], "target_sequences": genomes},
            {"strand": "both", "evalue_threshold": 1e-4, "domain_evalue_threshold": 1e-4, "num_threads": 4},
        )
        genome_text = fasta(sorted(zip(sample_ids, genomes, strict=True)))
        genome_path = context.workspace / "host_genomes.fasta"
        genome_path.write_text(genome_text)
        query_path = context.workspace / "boundary_probes.fasta"
        query_path.write_text(
            fasta([("Left_boundary", left), ("Internal_marker", internal), ("Right_boundary", right)])
        )
        db_prefix = context.workspace / "host_db"
        database = runtime.run_tool(
            "blast-create-db",
            {"fasta": str(genome_path)},
            {"dbtype": "nucl", "out_prefix": str(db_prefix), "parse_seqids": True},
        )
        local_hits = runtime.run_tool(
            "blast-search",
            {"query": str(query_path)},
            {
                "local_db": database["db_path"],
                "program": "blastn",
                "task": "blastn",
                "word_size": 9,
                "evalue": 1e-5,
                "qcov_hsp_perc": 60,
                "num_threads": 4,
                "max_target_seqs": config.num_genomes,
            },
        )
        gene_calls = runtime.run_tool(
            "prodigal-prediction",
            {"input_sequences": genomes},
            {"meta_mode": True, "closed_ends": False, "min_gene": 90, "num_threads": 4},
        )
        target_orfs = [
            orf
            for orf in gene_calls["results"][0]["orfs"]
            if orf["strand"] == "+" and orf["amino_acid_sequence"] == cargo
        ]
        target_hits = {hit["qseqid"] for hit in local_hits["hits"] if hit["sseqid"] == sample_ids[0]}
        if len(target_orfs) != 1 or target_hits != {"Left_boundary", "Internal_marker", "Right_boundary"}:
            raise RuntimeError("independent tools did not recover the injected complete element")
        host = sample_ids[0]
        interval = f"{positions[0] + 1}-{positions[0] + len(target_element)}"

        public_files = {
            "data/host_genomes.fasta": genome_text,
            "data/boundary_probes.fasta": query_path.read_text(),
            "data/cargo_marker.fasta": fasta([("Synthetic_cargo_marker", cargo)]),
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.INJECTED,
                facts={
                    "raw_genomes": dict(zip(raw_ids, genomes, strict=True)),
                    "injected_roles": {
                        raw_ids[0]: "complete_forward_intact",
                        raw_ids[1]: "complete_reverse_interrupted_cargo",
                        raw_ids[2]: "missing_right_boundary",
                        raw_ids[3]: "scrambled_boundaries",
                        raw_ids[4]: "internal_only",
                    },
                    "host": host,
                    "element_interval": interval,
                    "orientation": "+",
                    "cargo_orf": target_orfs[0],
                },
                anonymization_map=mapping,
                evidence={
                    "coarse_genome_search": coarse,
                    "profile_nucleotide_search": nhmmer,
                    "local_boundary_hits": local_hits,
                    "gene_calls": gene_calls,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.INJECTED,
                assertions=[
                    ExactAssertion(field="host", expected=host),
                    ExactAssertion(field="element_interval", expected=interval),
                    ExactAssertion(field="orientation", expected="+"),
                ],
                rubric_text=f"Credit requires host {host}, interval {interval}, and forward orientation.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Attribute a complete mobile element to its host and recover its boundaries",
                public_files=sorted(public_files),
                answer_format="host: Sample_...\nelement_interval: start-end\norientation: + or -",
                default_question=(
                    "The anonymous sequences in `data/host_genomes.fasta` contain partial insertions, reversed "
                    "decoys, rearranged boundary fragments, and one complete mobile element. Use the three probes "
                    "in `data/boundary_probes.fasta` together with the expected cargo family in "
                    "`data/cargo_marker.fasta` to identify the true host, the 1-based inclusive element interval, "
                    "and its orientation. The accepted call must reconcile broad nucleotide homology, exact local "
                    "boundary order, strand, element completeness, and an intact cargo coding region."
                ),
            ),
        )


MOBILE_ELEMENT_FAMILY = MobileElementFamily()
