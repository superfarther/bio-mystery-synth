from __future__ import annotations

from pathlib import Path

from bio_mystery_synth.core import ScenarioSpec
from bio_mystery_synth.sources.base import SourceBundle
from bio_mystery_synth.sources.closed_world import ClosedWorldSource
from bio_mystery_synth.sources.external_reference import (
    ExternalReferenceSource,
    LocalReferenceProvider,
    ReferenceProvider,
)

_REFERENCE_PROVIDERS: dict[str, ReferenceProvider] = {"local-file": LocalReferenceProvider()}


def register_reference_provider(name: str, provider: ReferenceProvider) -> None:
    if name in _REFERENCE_PROVIDERS:
        raise ValueError(f"duplicate reference provider: {name}")
    _REFERENCE_PROVIDERS[name] = provider


def get_reference_provider(name: str) -> ReferenceProvider:
    try:
        return _REFERENCE_PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(f"unknown reference provider: {name}") from exc


def materialize_source(spec: ScenarioSpec, workspace: Path) -> SourceBundle:
    if spec.source_kind == "closed-world":
        return ClosedWorldSource().materialize(spec, workspace)
    if spec.source_kind == "external-reference":
        return ExternalReferenceSource().materialize(spec, workspace)
    raise ValueError(f"unknown source: {spec.source_kind}")
