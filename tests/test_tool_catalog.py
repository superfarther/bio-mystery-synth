from __future__ import annotations

import pytest

from bio_mystery_synth.models import Backend, ExecutionSpec
from bio_mystery_synth.runtime import ProtoRuntime, capability_catalog
from bio_mystery_synth.tool_catalog import CURATED_TOOLS, NEW_CPU_TOOLS, NEW_GPU_TOOLS, apply_closed_world_config


def test_curated_catalog_is_available_and_closed_world() -> None:
    pytest.importorskip("proto_tools")
    catalog = capability_catalog()
    assert len(CURATED_TOOLS) == 39
    assert set(catalog["tools"]) == CURATED_TOOLS
    assert catalog["unavailable_tools"] == []
    assert all(tool["category"] != "database_retrieval" for tool in catalog["tools"].values())


def test_new_gpu_and_cpu_tools_have_expected_execution_class() -> None:
    module = pytest.importorskip("proto_tools.tools")

    assert len(NEW_GPU_TOOLS) == len(NEW_CPU_TOOLS) == 4
    assert all(module.ToolRegistry.get(tool).uses_gpu for tool in NEW_GPU_TOOLS)
    assert all(not module.ToolRegistry.get(tool).uses_gpu for tool in NEW_CPU_TOOLS)


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


def test_remote_foldmason_is_rejected() -> None:
    with pytest.raises(ValueError, match="closed-world generation requires"):
        apply_closed_world_config("foldmason-msa", {"search_mode": "remote"})


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
        runtime.run_tool("crispr-tracr-rna", {})
    assert runtime.calls[-1].tool == "crispr-tracr-rna"
    assert not runtime.calls[-1].ok
