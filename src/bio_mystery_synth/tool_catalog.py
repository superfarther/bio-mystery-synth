"""Compatibility exports for the tool catalog."""

from bio_mystery_synth.task_families.registry import family_definitions
from bio_mystery_synth.tools.catalog import CURATED_TOOLS, NEW_CPU_TOOLS, NEW_GPU_TOOLS, TOOL_GROUPS
from bio_mystery_synth.tools.policy import (
    CLOSED_WORLD_CONFIG,
    CLOSED_WORLD_REQUIRED_CONFIG,
    apply_closed_world_config,
)

FAMILY_TOOLS = {key: list(value.tools) for key, value in family_definitions().items()}

__all__ = [
    "CLOSED_WORLD_CONFIG",
    "CLOSED_WORLD_REQUIRED_CONFIG",
    "CURATED_TOOLS",
    "FAMILY_TOOLS",
    "NEW_CPU_TOOLS",
    "NEW_GPU_TOOLS",
    "TOOL_GROUPS",
    "apply_closed_world_config",
]
