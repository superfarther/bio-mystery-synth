from __future__ import annotations

from typing import Any

from bio_mystery_synth.task_families.registry import family_definitions
from bio_mystery_synth.tools.catalog import CURATED_TOOLS, TOOL_GROUPS
from bio_mystery_synth.tools.policy import CLOSED_WORLD_CONFIG, CLOSED_WORLD_REQUIRED_CONFIG


def declared_family_tools() -> dict[str, list[str]]:
    return {key: list(value.tools) for key, value in family_definitions().items()}


def capability_catalog() -> dict[str, Any]:
    catalog: dict[str, Any] = {
        "families": declared_family_tools(),
        "tool_groups": TOOL_GROUPS,
        "declared_tool_count": len(CURATED_TOOLS),
        "tools": {},
        "unavailable_tools": [],
    }
    try:
        from proto_tools.tools import ToolRegistry
    except ImportError:
        return catalog
    for tool in sorted(CURATED_TOOLS):
        try:
            spec = ToolRegistry.get(tool)
        except ValueError:
            catalog["unavailable_tools"].append(tool)
            continue
        catalog["tools"][tool] = {
            "category": spec.category,
            "description": spec.description,
            "uses_gpu": spec.uses_gpu,
            "supports_modal": not bool(spec.local_only),
            "required_config": CLOSED_WORLD_CONFIG.get(tool, {}),
            "required_config_fields": CLOSED_WORLD_REQUIRED_CONFIG.get(tool, ()),
            "input_schema": ToolRegistry.get_input_schema(tool),
            "config_schema": ToolRegistry.get_config_schema(tool),
        }
    return catalog
