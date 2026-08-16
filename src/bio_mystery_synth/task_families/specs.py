from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from bio_mystery_synth.core.scenario import FamilyConfig


class DNAMotifFamilySpec(FamilyConfig):
    kind: Literal["dna-motif-localization"] = "dna-motif-localization"
    num_sequences: int = Field(default=16, ge=4, le=128)
    sequence_length: int = Field(default=1000, ge=80, le=100_000)
    motif: str = Field(default="ACGTGCA", min_length=5, max_length=40, pattern=r"^[ACGT]+$")
    num_targets: int = Field(default=2, ge=1)
    num_decoys: int = Field(default=3, ge=0)
    gc_fraction: float = Field(default=0.5, ge=0.1, le=0.9)
    fimo_threshold: float = Field(default=1e-4, gt=0, le=1)

    @model_validator(mode="after")
    def validate_counts(self) -> DNAMotifFamilySpec:
        if self.num_targets + self.num_decoys > self.num_sequences:
            raise ValueError("targets and decoys exceed sequence count")
        return self


class RNAStructureFamilySpec(FamilyConfig):
    kind: Literal["rna-structure-ranking"] = "rna-structure-ranking"
    num_candidates: int = Field(default=8, ge=3, le=64)
    sequence_length: int = Field(default=120, ge=30, le=2000)
    mutation_counts: list[int] | None = None
    temperature: float = Field(default=37.0, ge=-273.15, le=100)
    min_score_gap: float = Field(default=0.01, ge=0, le=1)

    @model_validator(mode="after")
    def validate_mutations(self) -> RNAStructureFamilySpec:
        if self.mutation_counts is not None and len(self.mutation_counts) != self.num_candidates:
            raise ValueError("mutation_counts must match num_candidates")
        return self


class ProteinStructureFamilySpec(FamilyConfig):
    kind: Literal["protein-structure-nearest"] = "protein-structure-nearest"
    num_candidates: int = Field(default=6, ge=3, le=32)
    sequence_length: int = Field(default=140, ge=40, le=1000)
    mutation_counts: list[int] | None = None
    prediction_tool: str = "esmfold-prediction"
    alignment_tool: str = "tmalign-alignment"
    min_score_gap: float = Field(default=0.01, ge=0, le=1)

    @model_validator(mode="after")
    def validate_mutations(self) -> ProteinStructureFamilySpec:
        if self.mutation_counts is not None and len(self.mutation_counts) != self.num_candidates:
            raise ValueError("mutation_counts must match num_candidates")
        return self


class ProteinBridgeFamilySpec(FamilyConfig):
    kind: Literal["protein-bridge-triage"] = "protein-bridge-triage"
    num_candidates: int = Field(default=8, ge=6, le=16)
    sequence_length: int = Field(default=180, ge=80, le=500)
    anchor_divergence: float = Field(default=0.4, ge=0.2, le=0.7)
    candidate_noise: float = Field(default=0.06, ge=0.01, le=0.2)
    shortlist_size: int = Field(default=4, ge=3, le=8)
    min_score_gap: float = Field(default=1e-5, ge=0, le=0.1)

    @model_validator(mode="after")
    def validate_shortlist(self) -> ProteinBridgeFamilySpec:
        if self.shortlist_size >= self.num_candidates:
            raise ValueError("shortlist must be smaller than candidate set")
        return self


class CrisprLinkageFamilySpec(FamilyConfig):
    kind: Literal["crispr-spacer-linkage"] = "crispr-spacer-linkage"
    num_genomes: int = Field(default=24, ge=6, le=128)
    genome_length: int = Field(default=50_000, ge=5000, le=1_000_000)
    num_phages: int = Field(default=3, ge=2, le=12)
    phage_length: int = Field(default=20_000, ge=1000, le=200_000)
    num_targets: int = Field(default=3, ge=1)
    num_decoys: int = Field(default=6, ge=0)
    repeat: str = Field(default="GTTCACTGCCGTACAGGCAGCTTAGAAA", min_length=23, max_length=47, pattern=r"^[ACGT]+$")
    spacer_length: int = Field(default=32, ge=18, le=50)
    num_repeats: int = Field(default=8, ge=4, le=24)
    linked_spacers: int = Field(default=4, ge=1)

    @model_validator(mode="after")
    def validate_arrays(self) -> CrisprLinkageFamilySpec:
        if self.num_targets + self.num_decoys > self.num_genomes:
            raise ValueError("targets and decoys exceed genome count")
        if self.linked_spacers > self.num_repeats - 1:
            raise ValueError("linked_spacers exceeds available spacers")
        array_length = self.num_repeats * len(self.repeat) + (self.num_repeats - 1) * self.spacer_length
        if array_length > self.genome_length:
            raise ValueError("CRISPR array exceeds genome length")
        return self


class RecombinationFamilySpec(FamilyConfig):
    kind: Literal["windowed-recombination"] = "windowed-recombination"
    num_candidates: int = Field(default=48, ge=8, le=256)
    sequence_length: int = Field(default=4000, ge=500, le=50_000)
    num_recombinants: int = Field(default=3, ge=1)
    window_size: int = Field(default=200, ge=50, le=2000)
    clade_divergence: float = Field(default=0.12, ge=0.03, le=0.35)
    within_clade_divergence: float = Field(default=0.01, ge=0, le=0.05)

    @model_validator(mode="after")
    def validate_windows(self) -> RecombinationFamilySpec:
        if self.num_recombinants >= self.num_candidates:
            raise ValueError("recombinants must be fewer than candidates")
        if self.sequence_length % self.window_size:
            raise ValueError("sequence_length must be divisible by window_size")
        if self.sequence_length // self.window_size < 4:
            raise ValueError("at least four windows are required")
        return self


class UTRRegulatoryAssayFamilySpec(FamilyConfig):
    kind: Literal["utr-regulatory-assay"] = "utr-regulatory-assay"
    num_transcripts: int = Field(default=12, ge=8, le=64)
    coding_aa_length: int = Field(default=140, ge=80, le=500)
    utr_length: int = Field(default=320, ge=180, le=2000)
    num_mirnas: int = Field(default=4, ge=2, le=12)
    mirna_length: int = Field(default=22, ge=18, le=30)
    primer_pairs_per_transcript: int = Field(default=4, ge=3, le=12)
    fold_window: int = Field(default=100, ge=60, le=300)

    @model_validator(mode="after")
    def validate_fold_window(self) -> UTRRegulatoryAssayFamilySpec:
        if self.fold_window > self.utr_length:
            raise ValueError("fold window exceeds UTR length")
        return self


class MetagenomicEnzymeFamilySpec(FamilyConfig):
    kind: Literal["metagenomic-enzyme-forensics"] = "metagenomic-enzyme-forensics"
    num_contigs: int = Field(default=16, ge=10, le=64)
    contig_length: int = Field(default=12_000, ge=4000, le=100_000)
    protein_length: int = Field(default=180, ge=100, le=500)
    num_homologs: int = Field(default=6, ge=5, le=12)
    max_low_complexity: float = Field(default=0.25, ge=0, le=0.8)
    min_confidence_gap: float = Field(default=1e-5, ge=0, le=0.2)

    @model_validator(mode="after")
    def validate_homologs(self) -> MetagenomicEnzymeFamilySpec:
        if self.num_homologs >= self.num_contigs:
            raise ValueError("homolog count must be smaller than contig count")
        return self
