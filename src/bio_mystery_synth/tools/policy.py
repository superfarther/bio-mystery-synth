from __future__ import annotations

from typing import Any

from bio_mystery_synth.tools.catalog import CURATED_TOOLS

CLOSED_WORLD_CONFIG = {"blast-search": {"search_mode": "local"}}
CLOSED_WORLD_REQUIRED_CONFIG = {"blast-search": ("local_db",)}


def apply_closed_world_config(tool: str, config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(config)
    for key, required in CLOSED_WORLD_CONFIG.get(tool, {}).items():
        actual = merged.setdefault(key, required)
        if actual != required:
            raise ValueError(f"closed-world generation requires {tool}.{key}={required!r}")
    missing = [key for key in CLOSED_WORLD_REQUIRED_CONFIG.get(tool, ()) if not merged.get(key)]
    if missing:
        raise ValueError(f"closed-world generation requires {tool} config: {', '.join(missing)}")
    return merged


class ClosedWorldToolPolicy:
    def __init__(self, approved_tools: frozenset[str] = CURATED_TOOLS) -> None:
        self.approved_tools = approved_tools

    def prepare(self, tool: str, category: str, config: dict[str, Any]) -> dict[str, Any]:
        if category == "database_retrieval":
            raise ValueError(f"closed-world generation forbids {tool}")
        if tool not in self.approved_tools:
            raise ValueError(f"tool is not approved for closed-world generation: {tool}")
        return apply_closed_world_config(tool, config)
