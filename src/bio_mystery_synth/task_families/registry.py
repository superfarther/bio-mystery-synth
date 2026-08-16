from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from bio_mystery_synth.core.base import Difficulty
from bio_mystery_synth.core.scenario import FamilyConfig


class FamilyGenerator(Protocol):
    family_id: str
    config_model: type[FamilyConfig]
    defaults: dict[Difficulty, dict[str, Any]]
    tools: tuple[str, ...]
    supported_sources: tuple[str, ...]

    def generate(self, spec: Any, context: Any) -> Any: ...


@dataclass(frozen=True)
class FamilyDefinition:
    family_id: str
    config_model: type[FamilyConfig]
    generator: FamilyGenerator
    defaults: dict[Difficulty, dict[str, Any]]
    tools: tuple[str, ...]
    supported_sources: tuple[str, ...]

    def create_config(self, difficulty: Difficulty) -> FamilyConfig:
        return self.config_model(**self.defaults[difficulty])


T = TypeVar("T")


class FamilyRegistry:
    def __init__(self) -> None:
        self._families: dict[str, FamilyDefinition] = {}

    def register(self, family: T) -> T:
        instance = family() if isinstance(family, type) else family
        family_id = instance.family_id
        if family_id in self._families:
            raise ValueError(f"duplicate task family: {family_id}")
        self._families[family_id] = FamilyDefinition(
            family_id=family_id,
            config_model=instance.config_model,
            generator=instance,
            defaults=instance.defaults,
            tools=tuple(instance.tools),
            supported_sources=tuple(instance.supported_sources),
        )
        return family

    def get(self, family_id: str) -> FamilyDefinition:
        try:
            return self._families[family_id]
        except KeyError as exc:
            raise ValueError(f"unknown task family: {family_id}") from exc

    def definitions(self) -> dict[str, FamilyDefinition]:
        return dict(self._families)

    def validate_scenario(self, value: dict[str, Any]) -> Any:
        from bio_mystery_synth.core import ScenarioSpec

        payload = dict(value)
        family = payload.get("family")
        if not isinstance(family, dict) or not isinstance(family.get("kind"), str):
            raise ValueError("family requires a registered kind")
        payload["family"] = self.get(family["kind"]).config_model.model_validate(family)
        return ScenarioSpec.model_validate(payload)

    def validate_scenario_json(self, value: str) -> Any:
        return self.validate_scenario(json.loads(value))


BUILTIN_FAMILIES = FamilyRegistry()
_BUILTINS_LOADED = False


def register(family: T) -> T:
    return BUILTIN_FAMILIES.register(family)


def load_builtin_families() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True
    from bio_mystery_synth.task_families import builtins  # noqa: F401


def get_family_definition(family_id: str) -> FamilyDefinition:
    load_builtin_families()
    return BUILTIN_FAMILIES.get(family_id)


def get_family(family_id: str) -> FamilyGenerator:
    return get_family_definition(family_id).generator


def family_definitions() -> dict[str, FamilyDefinition]:
    load_builtin_families()
    return BUILTIN_FAMILIES.definitions()


def builtin_family_registry() -> FamilyRegistry:
    load_builtin_families()
    return BUILTIN_FAMILIES
