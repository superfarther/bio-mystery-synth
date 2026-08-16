from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, SerializeAsAny, field_validator, model_validator

from bio_mystery_synth.core.base import Backend, Difficulty, StrictModel


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


class FamilyConfig(StrictModel):
    kind: str


class ExternalReferenceSourceSpec(StrictModel):
    kind: Literal["external-reference"] = "external-reference"
    provider: str
    reference_id: str
    release: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScenarioSpec(StrictModel):
    schema_version: Literal["1", "2"] = "1"
    difficulty: Difficulty = Difficulty.MEDIUM
    seed: int = Field(ge=0)
    source: Literal["closed-world"] | ExternalReferenceSourceSpec = "closed-world"
    family: SerializeAsAny[FamilyConfig]
    entities: list[EntitySpec] = Field(default_factory=list)
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    interventions: list[InterventionSpec] = Field(default_factory=list)
    observations: list[ObservationSpec] = Field(default_factory=list)
    anonymization: AnonymizationSpec = Field(default_factory=AnonymizationSpec)
    execution: ExecutionSpec = Field(default_factory=ExecutionSpec)

    @field_validator("family", mode="before")
    @classmethod
    def parse_family(cls, value: Any) -> FamilyConfig:
        if isinstance(value, FamilyConfig):
            return value
        if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
            raise ValueError("family requires a registered kind")
        from bio_mystery_synth.task_families.registry import get_family_definition

        return get_family_definition(value["kind"]).config_model.model_validate(value)

    @model_validator(mode="after")
    def validate_source_version(self) -> ScenarioSpec:
        if isinstance(self.source, ExternalReferenceSourceSpec) and self.schema_version != "2":
            raise ValueError("external-reference scenarios require schema_version='2'")
        return self

    @property
    def task_family(self) -> str:
        return self.family.kind

    @property
    def source_kind(self) -> str:
        return self.source if isinstance(self.source, str) else self.source.kind
