"""Compatibility exports for task family registration."""

from collections.abc import Mapping

from bio_mystery_synth.task_families.registry import (
    FamilyDefinition,
    FamilyRegistry,
    builtin_family_registry,
    family_definitions,
    get_family,
    get_family_definition,
    register,
)


class _FamilyView(Mapping[str, object]):
    def _values(self) -> dict[str, object]:
        return {key: definition.generator for key, definition in family_definitions().items()}

    def __iter__(self):
        return iter(self._values())

    def __getitem__(self, key: str) -> object:
        return self._values()[key]

    def __len__(self) -> int:
        return len(self._values())


FAMILIES = _FamilyView()

__all__ = [
    "FAMILIES",
    "FamilyDefinition",
    "FamilyRegistry",
    "builtin_family_registry",
    "family_definitions",
    "get_family",
    "get_family_definition",
    "register",
]
