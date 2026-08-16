from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from bio_mystery_synth.core import ScenarioSpec


@dataclass(frozen=True)
class SourceAsset:
    provider: str
    reference_id: str
    kind: str
    path: Path
    sha256: str
    release: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceBundle:
    source_kind: str
    assets: tuple[SourceAsset, ...] = ()


class DataSource(Protocol):
    def materialize(self, spec: ScenarioSpec, workspace: Path) -> SourceBundle: ...
