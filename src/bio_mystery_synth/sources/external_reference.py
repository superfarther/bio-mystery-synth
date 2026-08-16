from __future__ import annotations

from pathlib import Path
from typing import Protocol

from bio_mystery_synth.core import ExternalReferenceSourceSpec, ScenarioSpec
from bio_mystery_synth.sources.base import SourceAsset, SourceBundle
from bio_mystery_synth.support.hashing import sha256


class ReferenceProvider(Protocol):
    def materialize(self, config: ExternalReferenceSourceSpec, workspace: Path) -> tuple[SourceAsset, ...]: ...


class LocalReferenceProvider:
    """Offline provider for prepared references and deterministic tests."""

    def materialize(self, config: ExternalReferenceSourceSpec, workspace: Path) -> tuple[SourceAsset, ...]:
        del workspace
        path_value = config.parameters.get("path")
        kind = config.parameters.get("kind", "sequence")
        if not isinstance(path_value, str):
            raise ValueError("local-file provider requires parameters.path")
        path = Path(path_value).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = sha256(path)
        if config.sha256 and config.sha256 != digest:
            raise ValueError(f"reference checksum mismatch: {config.reference_id}")
        return (
            SourceAsset(
                provider=config.provider,
                reference_id=config.reference_id,
                release=config.release,
                kind=str(kind),
                path=path,
                sha256=digest,
            ),
        )


class ExternalReferenceSource:
    def materialize(self, spec: ScenarioSpec, workspace: Path) -> SourceBundle:
        if not isinstance(spec.source, ExternalReferenceSourceSpec):
            raise ValueError(f"unsupported source: {spec.source_kind}")
        from bio_mystery_synth.sources.registry import get_reference_provider

        provider = get_reference_provider(spec.source.provider)
        return SourceBundle(
            source_kind=spec.source.kind,
            assets=provider.materialize(spec.source, workspace),
        )
