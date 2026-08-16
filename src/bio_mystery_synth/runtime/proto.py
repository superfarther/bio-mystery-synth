from __future__ import annotations

import time
from typing import Any

from bio_mystery_synth.core import Backend, ExecutionSpec
from bio_mystery_synth.core.manifest import ToolCallRecord
from bio_mystery_synth.tools.policy import ClosedWorldToolPolicy


class ProtoRuntime:
    """Lazy adapter over Proto packages; backend selection stays at this boundary."""

    def __init__(self, execution: ExecutionSpec, policy: ClosedWorldToolPolicy | None = None) -> None:
        self.execution = execution
        self.policy = policy or ClosedWorldToolPolicy()
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
            merged = self.policy.prepare(tool, spec.category, merged)
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
