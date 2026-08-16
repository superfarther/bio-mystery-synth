"""Genome-to-structure enzyme forensics family."""

from __future__ import annotations

import random
from pathlib import Path

from bio_mystery_synth.models import (
    AnswerSpec,
    ExactAssertion,
    FamilyResult,
    GroundTruth,
    MetagenomicEnzymeFamilySpec,
    OracleType,
    QuestionContext,
    ScenarioSpec,
)
from bio_mystery_synth.runtime import Runtime
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.utr_regulatory_assay import CODONS
from bio_mystery_synth.utils import anonymize, fasta


def _mutate(sequence: str, fraction: float, rng: random.Random) -> str:
    chars = list(sequence)
    positions = rng.sample(range(1, len(chars)), round((len(chars) - 1) * fraction))
    alphabet = "ACDEFGHIKLMNPQRSTVWY"
    for position in positions:
        chars[position] = rng.choice([aa for aa in alphabet if aa != chars[position]])
    return "".join(chars)


def _gene(sequence: str) -> str:
    return "AGGAGGAAAA" + "".join(CODONS[aa] for aa in sequence) + "TAA"


def _structure_text(value: dict[str, object]) -> str:
    structure = value.get("structure")
    if not isinstance(structure, str):
        raise RuntimeError("structure prediction returned no coordinates")
    return structure


def _composition_bias(sequence: str) -> float:
    return max(sequence.count(residue) for residue in set(sequence)) / len(sequence)


@register
class MetagenomicEnzymeFamily:
    family_id = "metagenomic-enzyme-forensics"

    def generate(self, spec: ScenarioSpec, runtime: Runtime, workspace: Path) -> FamilyResult:
        del workspace
        config = spec.family
        if not isinstance(config, MetagenomicEnzymeFamilySpec):
            raise TypeError("invalid metagenomic enzyme family spec")
        rng = random.Random(spec.seed)
        marker = "M" + runtime.generate_sequences("protein", 1, config.protein_length, spec.seed)[0][1:]
        homologs = [
            _mutate(marker, fraction, rng) for fraction in (0.05, 0.11, 0.18, 0.24, 0.30, 0.36)[: config.num_homologs]
        ]
        while len(homologs) < config.num_homologs:
            homologs.append(_mutate(marker, min(0.45, 0.06 * len(homologs)), rng))
        homologs[-2] = marker[: config.protein_length // 2]
        homologs[-1] = marker[: config.protein_length // 2] + "G" * (config.protein_length // 2)

        contigs = runtime.generate_sequences("dna", config.num_contigs, config.contig_length, spec.seed + 1, 0.5)
        raw_ids = [f"contig_{index:03d}" for index in range(1, config.num_contigs + 1)]
        intervals: dict[int, tuple[int, int]] = {}
        for index, protein in enumerate(homologs):
            gene = _gene(protein)
            start = 800 + index * 317
            contigs[index] = contigs[index][:start] + gene + contigs[index][start + len(gene) :]
            coding_start = start + 11
            intervals[index] = (coding_start, coding_start + len(protein) * 3 - 1)
        mapping = anonymize(raw_ids, spec.anonymization, rng)

        gene_calls = runtime.run_tool(
            "prodigal-prediction",
            {"input_sequences": contigs},
            {"meta_mode": True, "closed_ends": False, "min_gene": 90, "num_threads": 4},
        )
        called_intervals: dict[int, tuple[int, int]] = {}
        for index, protein in enumerate(homologs):
            matches = [
                orf
                for orf in gene_calls["results"][index]["orfs"]
                if orf["strand"] == "+" and orf["amino_acid_sequence"] == protein
            ]
            if len(matches) != 1:
                raise RuntimeError(f"gene caller did not recover homolog {index} uniquely")
            called_intervals[index] = (matches[0]["nucleotide_start"], matches[0]["nucleotide_end"])
        homology = runtime.run_tool(
            "pyhmmer-phmmer",
            {"sequences": [marker], "target_sequences": homologs},
            {"evalue_threshold": 1e-5, "domain_evalue_threshold": 1e-5, "num_threads": 4},
        )
        complexity = [_composition_bias(protein) for protein in homologs]
        shortlist = [
            index
            for index, (protein, bias) in enumerate(zip(homologs, complexity, strict=True))
            if 0.8 <= len(protein) / len(marker) <= 1.2 and bias <= config.max_low_complexity
        ]
        if len(shortlist) < 2:
            raise RuntimeError("composition and completeness triage left fewer than two homologs")
        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [marker, *(homologs[index] for index in shortlist)]},
            {"num_recycles": 4, "max_batch_residues": 1200},
        )["structures"]
        structures = [_structure_text(value) for value in predicted]
        shape = runtime.run_tool("structure-metrics", {"structures": structures}, {})["metrics"]
        confidence = [float(value["metrics"]["avg_plddt"]) for value in predicted[1:]]
        tm_scores = []
        for structure in structures[1:]:
            aligned = runtime.run_tool(
                "tmalign-alignment",
                {"query_structure": structure, "reference_structure": structures[0]},
                {},
            )
            tm_scores.append(float(aligned["metrics"]["tm_score_chain_2"]))
        reference_radius = float(shape[0]["gyration_radius"])
        scores = {
            index: 0.55 * confidence[position]
            + 0.4 * tm_scores[position]
            + 0.05 / (1 + abs(float(shape[position + 1]["gyration_radius"]) - reference_radius))
            for position, index in enumerate(shortlist)
        }
        ranking = sorted(scores, key=lambda index: (-scores[index], mapping[raw_ids[index]]))
        if len(ranking) > 1 and scores[ranking[0]] - scores[ranking[1]] < config.min_confidence_gap:
            raise RuntimeError("structural evidence has no unique winner")
        winner = ranking[0]
        winner_sample = mapping[raw_ids[winner]]
        interval = called_intervals[winner]

        public_files = {
            "data/contigs.fasta": fasta(
                sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, contigs, strict=True))
            ),
            "data/family_marker.fasta": fasta([("Synthetic_family_marker", marker)]),
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "raw_contigs": dict(zip(raw_ids, contigs, strict=True)),
                    "marker": marker,
                    "injected_homologs": dict(zip(raw_ids[: len(homologs)], homologs, strict=True)),
                    "injected_intervals": {raw_ids[index]: value for index, value in intervals.items()},
                    "called_intervals": {raw_ids[index]: value for index, value in called_intervals.items()},
                    "shortlist": [mapping[raw_ids[index]] for index in shortlist],
                    "confidence": dict(zip([mapping[raw_ids[index]] for index in shortlist], confidence, strict=True)),
                    "shape": dict(
                        zip(
                            ["Synthetic_family_marker", *[mapping[raw_ids[index]] for index in shortlist]],
                            shape,
                            strict=True,
                        )
                    ),
                    "tm_scores": dict(zip([mapping[raw_ids[index]] for index in shortlist], tm_scores, strict=True)),
                    "scores": {mapping[raw_ids[index]]: score for index, score in scores.items()},
                    "winner": winner_sample,
                    "winner_interval": interval,
                },
                anonymization_map=mapping,
                evidence={
                    "gene_calls": gene_calls,
                    "homology": homology,
                    "composition_bias": complexity,
                    "predicted_structures": predicted,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    ExactAssertion(field="sample", expected=winner_sample),
                    ExactAssertion(field="orf_interval", expected=f"{interval[0]}-{interval[1]}"),
                ],
                rubric_text=f"Credit requires {winner_sample} and ORF interval {interval[0]}-{interval[1]}.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Find the intact enzyme-family member hidden in anonymous metagenomic contigs",
                public_files=sorted(public_files),
                answer_format="sample: Sample_...\norf_interval: start-end",
                default_question=(
                    "`data/contigs.fasta` contains synthetic metagenomic fragments with truncated genes, "
                    "compositionally biased mimics, and several divergent relatives of the protein in "
                    "`data/family_marker.fasta`. Identify the single most credible intact family member and its "
                    "1-based inclusive coding interval, including the terminal stop codon when present. A defensible "
                    "call must reconcile prokaryotic gene boundaries, "
                    "statistically meaningful full-length homology, low compositional bias, and a compact, "
                    "high-confidence predicted fold; no one signal is sufficient on its own."
                ),
            ),
        )


METAGENOMIC_ENZYME_FAMILY = MetagenomicEnzymeFamily()
