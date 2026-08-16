"""Proto execution boundary."""

from __future__ import annotations

import time
from typing import Any, Protocol

from bio_mystery_synth.models import Backend, ExecutionSpec, ToolCallRecord
from bio_mystery_synth.tool_catalog import (
    CLOSED_WORLD_CONFIG,
    CLOSED_WORLD_REQUIRED_CONFIG,
    CURATED_TOOLS,
    FAMILY_TOOLS,
    TOOL_GROUPS,
    apply_closed_world_config,
)


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


class ProtoRuntime:
    """Lazy adapter over the proto-tools registry."""

    def __init__(self, execution: ExecutionSpec) -> None:
        self.execution = execution
        self.calls: list[ToolCallRecord] = []

    def run_tool(self, tool: str, inputs: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.monotonic()
        merged = {**(config or {}), **self.execution.tool_overrides.get(tool, {})}
        device = "modal" if self.execution.backend == Backend.MODAL else self.execution.local_device
        ok = False
        try:
            from proto_tools.tools import ToolRegistry

            spec = ToolRegistry.get(tool)
            if self.execution.backend == Backend.LOCAL and not spec.uses_gpu:
                device = "cpu"
            if spec.category == "database_retrieval":
                raise ValueError(f"closed-world generation forbids {tool}")
            if tool not in CURATED_TOOLS:
                raise ValueError(f"tool is not approved for closed-world generation: {tool}")
            merged = apply_closed_world_config(tool, merged)
            if self.execution.backend == Backend.LOCAL and spec.uses_gpu and not device.startswith("cuda"):
                raise ValueError(f"{tool} requires a GPU; configure cuda or use Modal")
            payload = spec.input_model(**inputs)
            cfg = spec.config_model(**{**merged, "device": device})
            output = spec.function(payload, cfg)
            ok = True
            return output.model_dump(mode="json")
        finally:
            self.calls.append(
                ToolCallRecord(
                    tool=tool,
                    backend=self.execution.backend,
                    device=device,
                    config=merged,
                    duration_seconds=round(time.monotonic() - started, 6),
                    ok=ok,
                )
            )

    def generate_sequences(
        self,
        sequence_type: str,
        count: int,
        length: int,
        seed: int,
        gc_fraction: float | None = None,
    ) -> list[str]:
        started = time.monotonic()
        ok = False
        device = "modal" if self.execution.backend == Backend.MODAL else "cpu"
        try:
            from proto_language.constraint import gc_content_constraint, sequence_length_constraint
            from proto_language.core import Constraint, Construct, Program, Segment
            from proto_language.generator import (
                RandomNucleotideGenerator,
                RandomNucleotideGeneratorConfig,
                RandomProteinGenerator,
                RandomProteinGeneratorConfig,
            )
            from proto_language.optimizer import RejectionSamplingOptimizer, RejectionSamplingOptimizerConfig

            segment = Segment(length=length, sequence_type=sequence_type)
            construct = Construct([segment])
            if sequence_type == "protein":
                generator = RandomProteinGenerator(RandomProteinGeneratorConfig())
            else:
                generator = RandomNucleotideGenerator(RandomNucleotideGeneratorConfig())
            generator.assign(segment)
            constraints = [
                Constraint(
                    inputs=[segment],
                    function=sequence_length_constraint,
                    function_config={"target_length": length},
                )
            ]
            if gc_fraction is not None:
                margin = 3.0
                constraints.append(
                    Constraint(
                        inputs=[segment],
                        function=gc_content_constraint,
                        function_config={
                            "min_gc": max(0.0, gc_fraction * 100 - margin),
                            "max_gc": min(100.0, gc_fraction * 100 + margin),
                        },
                    )
                )
            optimizer = RejectionSamplingOptimizer(
                constructs=[construct],
                generators=[generator],
                constraints=constraints,
                config=RejectionSamplingOptimizerConfig(
                    num_samples=max(count * 3, count),
                    num_results=count,
                    proposal_batch_size=count,
                ),
            )
            program = Program(optimizers=[optimizer], num_results=count, seed=seed)
            program.run(device="modal" if self.execution.backend == Backend.MODAL else None)
            ok = True
            return [sequence.sequence for sequence in program.constructs[0].joined_sequences]
        finally:
            self.calls.append(
                ToolCallRecord(
                    tool=f"proto-language:random-{sequence_type}",
                    backend=self.execution.backend,
                    device=device,
                    config={"count": count, "length": length, "gc_fraction": gc_fraction},
                    duration_seconds=round(time.monotonic() - started, 6),
                    ok=ok,
                )
            )


DECLARED_TOOLS = FAMILY_TOOLS


def capability_catalog() -> dict[str, Any]:
    catalog: dict[str, Any] = {
        "families": DECLARED_TOOLS,
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
