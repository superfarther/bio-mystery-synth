"""Biological source abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bio_mystery_synth.models import ScenarioSpec


@dataclass(frozen=True)
class SourceBundle:
    source: str


class DataSource(Protocol):
    def materialize(self, spec: ScenarioSpec) -> SourceBundle: ...


class ClosedWorldSource:
    def materialize(self, spec: ScenarioSpec) -> SourceBundle:
        if spec.source != "closed-world":
            raise ValueError(f"unsupported source: {spec.source}")
        return SourceBundle(source=spec.source)
