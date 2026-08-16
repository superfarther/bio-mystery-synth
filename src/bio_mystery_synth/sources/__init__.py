from bio_mystery_synth.sources.base import DataSource, SourceAsset, SourceBundle
from bio_mystery_synth.sources.closed_world import ClosedWorldSource
from bio_mystery_synth.sources.external_reference import ExternalReferenceSource, LocalReferenceProvider
from bio_mystery_synth.sources.registry import (
    get_reference_provider,
    materialize_source,
    register_reference_provider,
)

__all__ = [
    "ClosedWorldSource",
    "DataSource",
    "ExternalReferenceSource",
    "LocalReferenceProvider",
    "SourceAsset",
    "SourceBundle",
    "get_reference_provider",
    "materialize_source",
    "register_reference_provider",
]
