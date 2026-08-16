from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from bio_mystery_synth.core.base import Backend, Difficulty, StrictModel


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


class SourceAssetRecord(StrictModel):
    provider: str
    reference_id: str
    release: str | None = None
    kind: str
    sha256: str
    cached_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    source_kind: str
    assets: list[SourceAssetRecord]
