"""Proto execution boundary."""

from __future__ import annotations

import time
from typing import Any, Protocol

from bio_mystery_synth.models import Backend, ExecutionSpec, ToolCallRecord


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
            if spec.category == "database_retrieval":
                raise ValueError(f"closed-world generation forbids {tool}")
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
        device = "modal" if self.execution.backend == Backend.MODAL else self.execution.local_device
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


DECLARED_TOOLS = {
    "dna-motif-localization": ["random-nucleotide-sample", "meme-fimo-scan"],
    "rna-structure-ranking": ["random-nucleotide-sample", "viennarna-prediction"],
    "protein-structure-nearest": [
        "random-protein-sample",
        "esmfold-prediction",
        "tmalign-alignment",
    ],
    "protein-bridge-triage": [
        "random-protein-sample",
        "esmfold-prediction",
        "structure-metrics",
        "tmalign-alignment",
        "mafft-align",
    ],
    "crispr-spacer-linkage": ["minced-crispr"],
    "windowed-recombination": ["mafft-align"],
}


def capability_catalog() -> dict[str, Any]:
    catalog: dict[str, Any] = {"families": DECLARED_TOOLS, "tools": {}}
    try:
        from proto_tools.tools import ToolRegistry
    except ImportError:
        return catalog
    allowed = {tool for tools in DECLARED_TOOLS.values() for tool in tools}
    for tool in sorted(allowed):
        try:
            spec = ToolRegistry.get(tool)
        except ValueError:
            continue
        catalog["tools"][tool] = {
            "description": spec.description,
            "uses_gpu": spec.uses_gpu,
            "input_schema": ToolRegistry.get_input_schema(tool),
            "config_schema": ToolRegistry.get_config_schema(tool),
        }
    return catalog
