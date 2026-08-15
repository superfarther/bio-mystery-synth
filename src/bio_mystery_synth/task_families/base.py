"""Task family registry."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeVar

from bio_mystery_synth.models import FamilyResult, ScenarioSpec
from bio_mystery_synth.runtime import Runtime


class TaskFamily(Protocol):
    family_id: str

    def generate(self, spec: ScenarioSpec, runtime: Runtime, workspace: Path) -> FamilyResult: ...


FAMILIES: dict[str, TaskFamily] = {}
T = TypeVar("T")


def register(family: T) -> T:
    instance = family() if isinstance(family, type) else family
    FAMILIES[instance.family_id] = instance
    return family


def get_family(family_id: str) -> TaskFamily:
    try:
        return FAMILIES[family_id]
    except KeyError as exc:
        raise ValueError(f"unknown task family: {family_id}") from exc
