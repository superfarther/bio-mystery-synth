from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from bio_mystery_synth.core.base import OracleType, StrictModel


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
