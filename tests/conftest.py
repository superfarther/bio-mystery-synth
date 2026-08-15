from __future__ import annotations

import random
import re
import time
from typing import Any

from bio_mystery_synth.models import Backend, ToolCallRecord


class FakeRuntime:
    def __init__(self, seed: int = 1) -> None:
        self.rng = random.Random(seed)
        self.calls: list[ToolCallRecord] = []

    def _record(self, tool: str, config: dict[str, Any] | None = None) -> None:
        self.calls.append(
            ToolCallRecord(
                tool=tool,
                backend=Backend.LOCAL,
                device="cpu",
                config=config or {},
                duration_seconds=0.0,
                ok=True,
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
        del seed, gc_fraction
        alphabet = {"dna": "ACGT", "rna": "ACGU", "protein": "ACDEFGHIKLMNPQRSTVWY"}[sequence_type]
        self._record(f"proto-language:random-{sequence_type}")
        return ["".join(self.rng.choice(alphabet) for _ in range(length)) for _ in range(count)]

    def run_tool(self, tool: str, inputs: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.monotonic()
        if tool == "random-nucleotide-sample":
            alphabet = "ACGU"
            results = []
            for candidate_index, sequence in enumerate(inputs["sequences"]):
                chars = [
                    alphabet[(position + candidate_index) % len(alphabet)] if char == "_" else char
                    for position, char in enumerate(sequence)
                ]
                results.append({"sequence": "".join(chars)})
            output = {"results": results}
        elif tool == "random-protein-sample":
            alphabet = "ACDEFGHIKLMNPQRSTVWY"
            results = []
            for candidate_index, sequence in enumerate(inputs["sequences"]):
                chars = [
                    alphabet[(position + candidate_index) % len(alphabet)] if char == "_" else char
                    for position, char in enumerate(sequence)
                ]
                results.append({"sequence": "".join(chars)})
            output = {"results": results}
        elif tool == "meme-fimo-scan":
            output = {"results": [{"matches": []} for _ in inputs["sequences"]]}
        elif tool == "viennarna-prediction":
            results = []
            for index, sequence in enumerate(inputs["sequences"]):
                pairs = max(1, min(8, len(sequence) // 3) - index)
                structure = "(" * pairs + "." * (len(sequence) - 2 * pairs) + ")" * pairs
                results.append({"sequence": sequence, "structure": structure, "mfe": -float(pairs)})
            output = {"results": results}
        elif tool == "esmfold-prediction":
            output = {
                "structures": [
                    {"structure": f"MODEL {index}\nEND\n", "structure_format": "pdb"}
                    for index, _ in enumerate(inputs["complexes"])
                ]
            }
        elif tool == "tmalign-alignment":
            match = re.search(r"MODEL (\d+)", inputs["query_structure"])
            index = int(match.group(1)) if match else 9
            output = {"metrics": {"tm_score_chain_1": 1 - index / 10, "tm_score_chain_2": 1 - index / 10}}
        else:
            raise ValueError(tool)
        self.calls.append(
            ToolCallRecord(
                tool=tool,
                backend=Backend.LOCAL,
                device="cpu",
                config=config or {},
                duration_seconds=time.monotonic() - started,
                ok=True,
            )
        )
        return output
