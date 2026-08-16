from pathlib import Path

from bio_mystery_synth.core import ScenarioSpec
from bio_mystery_synth.sources.base import SourceBundle


class ClosedWorldSource:
    def materialize(self, spec: ScenarioSpec, workspace: Path | None = None) -> SourceBundle:
        del workspace
        if spec.source_kind != "closed-world":
            raise ValueError(f"unsupported source: {spec.source_kind}")
        return SourceBundle(source_kind="closed-world")
