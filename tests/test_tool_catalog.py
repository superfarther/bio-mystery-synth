from __future__ import annotations

import pytest

from bio_mystery_synth.models import Backend, ExecutionSpec
from bio_mystery_synth.runtime import ProtoRuntime, capability_catalog
from bio_mystery_synth.tool_catalog import CURATED_TOOLS, apply_closed_world_config


def test_curated_catalog_is_available_and_closed_world() -> None:
    pytest.importorskip("proto_tools")
    catalog = capability_catalog()
    assert len(CURATED_TOOLS) >= 30
    assert set(catalog["tools"]) == CURATED_TOOLS
    assert catalog["unavailable_tools"] == []
    assert all(tool["category"] != "database_retrieval" for tool in catalog["tools"].values())


def test_curated_tool_schemas_and_required_configs_validate() -> None:
    module = pytest.importorskip("proto_tools.tools")

    catalog = capability_catalog()
    for key, metadata in catalog["tools"].items():
        spec = module.ToolRegistry.get(key)
        spec.input_model.model_json_schema()
        required = {field: "/tmp/case-artifact" for field in metadata["required_config_fields"]}
        spec.config_model(**metadata["required_config"], **required, device="cpu")


def test_remote_search_is_rejected() -> None:
    with pytest.raises(ValueError, match="closed-world generation requires"):
        apply_closed_world_config("blast-search", {"search_mode": "online"})


def test_blast_requires_case_local_database() -> None:
    with pytest.raises(ValueError, match="local_db"):
        apply_closed_world_config("blast-search", {})


def test_database_tool_is_rejected_and_recorded() -> None:
    pytest.importorskip("proto_tools")
    runtime = ProtoRuntime(ExecutionSpec(backend=Backend.LOCAL, local_device="cpu"))
    with pytest.raises(ValueError, match="closed-world generation forbids"):
        runtime.run_tool("alphafold-db-fetch", {})
    assert runtime.calls[-1].tool == "alphafold-db-fetch"
    assert not runtime.calls[-1].ok


def test_uncurated_tool_is_rejected_and_recorded() -> None:
    pytest.importorskip("proto_tools")
    runtime = ProtoRuntime(ExecutionSpec(backend=Backend.LOCAL, local_device="cpu"))
    with pytest.raises(ValueError, match="not approved"):
        runtime.run_tool("esm2-score", {})
    assert runtime.calls[-1].tool == "esm2-score"
    assert not runtime.calls[-1].ok
