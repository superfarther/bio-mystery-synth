from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from bio_mystery_synth.artifacts import ArtifactStore
from bio_mystery_synth.synthesis import SynthesisRegistry


@dataclass(frozen=True)
class GenerationContext:
    runtime: object
    workspace: Path
    source: object
    artifacts: ArtifactStore
    rng: random.Random
    synthesis: SynthesisRegistry
