from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class SynthesisResult:
    payload: Any
    facts: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)


class Intervention(Protocol):
    def apply(
        self,
        payload: Any,
        parameters: dict[str, Any],
        workspace: Path,
        rng: random.Random,
    ) -> SynthesisResult: ...


class ObservationSimulator(Protocol):
    def simulate(
        self,
        payload: Any,
        parameters: dict[str, Any],
        workspace: Path,
        rng: random.Random,
    ) -> SynthesisResult: ...
