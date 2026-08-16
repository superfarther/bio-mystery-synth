"""Large-cohort metagenomic stability forensics."""

from __future__ import annotations

import random

from bio_mystery_synth.biology import CODONS, fasta
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
from bio_mystery_synth.task_families.advanced_protein import cosine, mutate, normalize, structure_text
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import MetagenomicStabilityFamilySpec

_MODEL = "esm2_t6_8M_UR50D"


def _gene(protein: str) -> str:
    return "AGGAGGAAAA" + "".join(CODONS[residue] for residue in protein) + "TAA"


def _bias(sequence: str) -> float:
    return max(sequence.count(residue) for residue in set(sequence)) / len(sequence)


@register
class MetagenomicStabilityFamily:
    family_id = "metagenomic-stability-forensics"
    config_model = MetagenomicStabilityFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(
            num_contigs=64, contig_length=15_000, protein_length=160, num_homologs=10, finalist_count=5
        ),
        Difficulty.MEDIUM: dict(
            num_contigs=96, contig_length=20_000, protein_length=190, num_homologs=13, finalist_count=7
        ),
        Difficulty.HARD: dict(
            num_contigs=128, contig_length=25_000, protein_length=220, num_homologs=16, finalist_count=8
        ),
    }
    tools = (
        "prodigal-prediction",
        "pyhmmer-phmmer",
        "esm2-score",
        "esm2-embedding",
        "esmfold-prediction",
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
        if not isinstance(config, MetagenomicStabilityFamilySpec):
            raise TypeError("invalid metagenomic stability family spec")
        rng = random.Random(spec.seed)
        marker = "M" + runtime.generate_sequences("protein", 1, config.protein_length, spec.seed)[0][1:]
        homologs = [
            mutate(marker, round(config.protein_length * (0.07 + 0.38 * index / (config.num_homologs - 1))), rng)
            for index in range(config.num_homologs)
        ]
        homologs[-3] = homologs[-3][: config.protein_length // 2]
        homologs[-2] = homologs[-2][: config.protein_length // 2] + "G" * (config.protein_length // 2)
        pivot = config.protein_length // 2
        homologs[-1] = homologs[-1][pivot:] + homologs[-1][:pivot]
        contigs = runtime.generate_sequences("dna", config.num_contigs, config.contig_length, spec.seed + 1, 0.5)
        raw_ids = [f"metacontig_{index:03d}" for index in range(1, config.num_contigs + 1)]
        injected: dict[int, tuple[int, int]] = {}
        for index, protein in enumerate(homologs):
            gene = _gene(protein)
            start = 1200 + index * 911
            contigs[index] = contigs[index][:start] + gene + contigs[index][start + len(gene) :]
            injected[index] = (start + 11, start + 10 + len(protein) * 3 + 3)
        mapping = anonymize(raw_ids, spec.anonymization, rng)

        called = runtime.run_tool(
            "prodigal-prediction",
            {"input_sequences": contigs},
            {"meta_mode": True, "closed_ends": False, "min_gene": 90, "num_threads": 8},
        )
        intervals: dict[int, tuple[int, int]] = {}
        for index, protein in enumerate(homologs):
            matches = [
                orf
                for orf in called["results"][index]["orfs"]
                if orf["strand"] == "+" and orf["amino_acid_sequence"] == protein
            ]
            if len(matches) == 1:
                intervals[index] = (int(matches[0]["nucleotide_start"]), int(matches[0]["nucleotide_end"]))
        expected = set(range(config.num_homologs - 3))
        if not expected <= intervals.keys():
            raise RuntimeError("gene caller did not recover every complete homolog")
        homology = runtime.run_tool(
            "pyhmmer-phmmer",
            {"sequences": [marker], "target_sequences": homologs},
            {"evalue_threshold": 1e-4, "domain_evalue_threshold": 1e-4, "num_threads": 8},
        )
        eligible = [
            index
            for index, protein in enumerate(homologs)
            if index in intervals and 0.85 <= len(protein) / len(marker) <= 1.15 and _bias(protein) <= 0.22
        ]
        language = runtime.run_tool(
            "esm2-score",
            {"sequences": [homologs[index] for index in eligible]},
            {"model_checkpoint": _MODEL, "batch_size": 16},
        )["scores"]
        embedded = runtime.run_tool(
            "esm2-embedding",
            {"sequences": [marker, *(homologs[index] for index in eligible)]},
            {"model_checkpoint": _MODEL, "batch_size": 16},
        )["results"]
        similarities = [cosine(embedded[0]["mean_embedding"], item["mean_embedding"]) for item in embedded[1:]]
        plausibility = normalize([float(item["perplexity"]) for item in language], False)
        proximity = normalize(similarities)
        preliminary = {
            index: 0.55 * plausibility[position] + 0.45 * proximity[position] for position, index in enumerate(eligible)
        }
        finalists = sorted(eligible, key=lambda index: (-preliminary[index], mapping[raw_ids[index]]))[
            : config.finalist_count
        ]

        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [marker, *(homologs[index] for index in finalists)]},
            {"num_recycles": 6, "max_batch_residues": 1320, "seed": spec.seed},
        )["structures"]
        structures = [structure_text(item) for item in predicted]
        labels = ["Marker", *[f"F{position:02d}" for position in range(1, len(finalists) + 1)]]
        structure_alignment = runtime.run_tool(
            "foldmason-msa",
            {"structures": structures, "structure_ids": labels},
            {"search_mode": "local", "refine_iters": 2, "precluster": True, "num_threads": 8},
        )
        alignment_score = runtime.run_tool(
            "foldmason-score-msa",
            {"structures": structures, "structure_ids": labels, "msa": structure_alignment["aa_msa_fasta"]},
            {"num_threads": 8},
        )
        clusters = runtime.run_tool(
            "foldseek-cluster",
            {"structures": structures, "structure_ids": labels},
            {"cov": 0.75, "alignment_type": 1, "tmscore_threshold": 0.45, "num_threads": 8},
        )
        secondary = runtime.run_tool("dssp-secondary-structure", {"inputs": structures}, {})["results"]
        energies = runtime.run_tool("pyrosetta-energy", {"inputs": structures}, {})["results"]
        sasa = runtime.run_tool("pyrosetta-sasa", {"inputs": structures}, {})["results"]
        tm_scores = []
        for structure in structures[1:]:
            result = runtime.run_tool(
                "usalign-alignment",
                {"query_structure": structure, "reference_structure": structures[0]},
                {},
            )
            tm_scores.append(float(result["metrics"]["tm_score_structure_2"]))
        energy = [
            float(item["total_energy"]) / len(homologs[index])
            for item, index in zip(energies[1:], finalists, strict=True)
        ]
        exposure = [
            float(item["total_sasa"]) / len(homologs[index]) for item, index in zip(sasa[1:], finalists, strict=True)
        ]
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
        components = list(
            zip(
                normalize(tm_scores),
                normalize(energy, False),
                normalize(exposure, False),
                normalize(ss_similarity),
                normalize(confidence),
                strict=True,
            )
        )
        scores = {
            index: 0.15 * preliminary[index]
            + 0.3 * tm
            + 0.2 * energy_score
            + 0.1 * compactness
            + 0.1 * ss
            + 0.15 * quality
            for index, (tm, energy_score, compactness, ss, quality) in zip(finalists, components, strict=True)
        }
        ranked_indexes = sorted(finalists, key=lambda index: (-scores[index], mapping[raw_ids[index]]))[:3]
        ranking = [f"{mapping[raw_ids[index]]}:{intervals[index][0]}-{intervals[index][1]}" for index in ranked_indexes]
        public_files = {
            "data/contigs.fasta": fasta(
                sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, contigs, strict=True))
            ),
            "data/family_marker.fasta": fasta([("Synthetic_marker", marker)]),
            "data/family_marker.pdb": structures[0],
        }
        finalist_ids = [mapping[raw_ids[index]] for index in finalists]
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "raw_contigs": dict(zip(raw_ids, contigs, strict=True)),
                    "marker": marker,
                    "injected_homologs": {raw_ids[index]: homologs[index] for index in range(config.num_homologs)},
                    "injected_intervals": {raw_ids[index]: value for index, value in injected.items()},
                    "called_intervals": {mapping[raw_ids[index]]: value for index, value in intervals.items()},
                    "eligible": [mapping[raw_ids[index]] for index in eligible],
                    "preliminary_scores": {mapping[raw_ids[index]]: preliminary[index] for index in eligible},
                    "finalists": finalist_ids,
                    "tm_scores": dict(zip(finalist_ids, tm_scores, strict=True)),
                    "energy_per_residue": dict(zip(finalist_ids, energy, strict=True)),
                    "sasa_per_residue": dict(zip(finalist_ids, exposure, strict=True)),
                    "secondary_similarity": dict(zip(finalist_ids, ss_similarity, strict=True)),
                    "final_scores": {mapping[raw_ids[index]]: scores[index] for index in finalists},
                    "top_three": ranking,
                },
                anonymization_map=mapping,
                evidence={
                    "gene_calls": called,
                    "homology": homology,
                    "language_scores": language,
                    "embeddings": embedded,
                    "predictions": predicted,
                    "structural_alignment": structure_alignment,
                    "alignment_score": alignment_score,
                    "clusters": clusters,
                    "secondary_structure": secondary,
                    "energies": energies,
                    "sasa": sasa,
                },
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[RankingAssertion(field="top_three_orfs", expected=ranking)],
                rubric_text="Credit requires the top three sample/ORF calls in order: " + " > ".join(ranking),
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Recover and rank stable enzyme-family members from a large anonymous metagenome",
                public_files=sorted(public_files),
                answer_format="top_three: Sample_...:start-end > Sample_...:start-end > Sample_...:start-end",
                default_question=(
                    "Search the complete anonymous contig collection under `data/` for intact relatives of the "
                    "supplied synthetic family marker. Exclude truncated, compositionally biased, and rearranged "
                    "mimics. From the remaining full-length relatives, report the three best-supported sample and "
                    "1-based inclusive coding intervals in order. The ranking must reconcile gene-boundary and "
                    "homology evidence with whole-sequence plausibility, family-space proximity, conserved fold and "
                    "secondary structure, physical energy, solvent exposure, and coordinate confidence; isolated "
                    "evidence is insufficient."
                ),
            ),
        )


METAGENOMIC_STABILITY_FAMILY = MetagenomicStabilityFamily()
