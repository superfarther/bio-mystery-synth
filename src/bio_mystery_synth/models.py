"""Persistent models shared by planning, generation, and grading."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Backend(StrEnum):
    LOCAL = "local"
    MODAL = "modal"


class OracleType(StrEnum):
    INJECTED = "injected_truth"
    DETERMINISTIC = "deterministic_computation"
    MODEL_DEFINED = "model_defined"


class EntitySpec(StrictModel):
    kind: Literal["dna", "rna", "protein", "sample"]
    count: int = Field(ge=1)
    length: int | None = Field(default=None, ge=1)


class ConstraintSpec(StrictModel):
    kind: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class InterventionSpec(StrictModel):
    kind: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ObservationSpec(StrictModel):
    name: str
    format: str


class AnonymizationSpec(StrictModel):
    sample_prefix: str = "Sample"
    width: int = Field(default=3, ge=2, le=8)
    shuffle: bool = True


class ExecutionSpec(StrictModel):
    backend: Backend = Backend.LOCAL
    local_device: str = "cuda"
    tool_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_device(self) -> ExecutionSpec:
        if self.backend == Backend.LOCAL and self.local_device in {"modal", "proto"}:
            raise ValueError("local backend requires a local device")
        return self


class DNAMotifFamilySpec(StrictModel):
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


class RNAStructureFamilySpec(StrictModel):
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


class ProteinStructureFamilySpec(StrictModel):
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


class CrisprLinkageFamilySpec(StrictModel):
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


class RecombinationFamilySpec(StrictModel):
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


FamilySpec = Annotated[
    DNAMotifFamilySpec
    | RNAStructureFamilySpec
    | ProteinStructureFamilySpec
    | CrisprLinkageFamilySpec
    | RecombinationFamilySpec,
    Field(discriminator="kind"),
]


class ScenarioSpec(StrictModel):
    schema_version: Literal["1"] = "1"
    difficulty: Difficulty = Difficulty.MEDIUM
    seed: int = Field(ge=0)
    source: Literal["closed-world"] = "closed-world"
    family: FamilySpec
    entities: list[EntitySpec] = Field(default_factory=list)
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    interventions: list[InterventionSpec] = Field(default_factory=list)
    observations: list[ObservationSpec] = Field(default_factory=list)
    anonymization: AnonymizationSpec = Field(default_factory=AnonymizationSpec)
    execution: ExecutionSpec = Field(default_factory=ExecutionSpec)

    @property
    def task_family(self) -> str:
        return self.family.kind


class ExactAssertion(StrictModel):
    kind: Literal["exact"] = "exact"
    field: str
    expected: str | int | float | bool
    case_sensitive: bool = False


class SetAssertion(StrictModel):
    kind: Literal["unordered_set"] = "unordered_set"
    field: str
    expected: list[str]


class NumericRangeAssertion(StrictModel):
    kind: Literal["numeric_range"] = "numeric_range"
    field: str
    minimum: float
    maximum: float


class RankingAssertion(StrictModel):
    kind: Literal["ranking"] = "ranking"
    field: str
    expected: list[str]
    require_complete: bool = True


AnswerAssertion = Annotated[
    ExactAssertion | SetAssertion | NumericRangeAssertion | RankingAssertion,
    Field(discriminator="kind"),
]


class AnswerSpec(StrictModel):
    schema_version: Literal["1"] = "1"
    oracle_type: OracleType
    assertions: list[AnswerAssertion]
    rubric_text: str


class GroundTruth(StrictModel):
    schema_version: Literal["1"] = "1"
    oracle_type: OracleType
    facts: dict[str, Any]
    anonymization_map: dict[str, str]
    evidence: dict[str, Any] = Field(default_factory=dict)


class QuestionContext(StrictModel):
    task_family: str
    goal: str
    public_files: list[str]
    answer_format: str
    default_question: str


class QuestionDraft(StrictModel):
    title: str
    prompt: str
    expected_response_format: str
    referenced_files: list[str]


class ToolCallRecord(StrictModel):
    tool: str
    backend: Backend
    device: str
    config: dict[str, Any]
    duration_seconds: float
    ok: bool


class GenerationManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    case_id: str
    status: Literal["complete", "failed"]
    seed: int
    backend: Backend
    tool_calls: list[ToolCallRecord]
    public_files: list[str]
    file_sha256: dict[str, str]


class CaseIndexEntry(StrictModel):
    case_id: str
    task_family: str
    difficulty: Difficulty
    seed: int
    backend: Backend
    tools: list[str]
    public_path: str
    answer_path: str


class FamilyResult(StrictModel):
    public_files: dict[str, str]
    ground_truth: GroundTruth
    answer: AnswerSpec
    question_context: QuestionContext


class GeneratedCase(StrictModel):
    case_id: str
    path: Path
    index: CaseIndexEntry
