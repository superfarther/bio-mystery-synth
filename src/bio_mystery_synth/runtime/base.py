from __future__ import annotations

from typing import Any, Protocol

from bio_mystery_synth.core.manifest import ToolCallRecord


class Runtime(Protocol):
    calls: list[ToolCallRecord]

    def run_tool(self, tool: str, inputs: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def generate_sequences(
        self,
        sequence_type: str,
        count: int,
        length: int,
        seed: int,
        gc_fraction: float | None = None,
    ) -> list[str]: ...
