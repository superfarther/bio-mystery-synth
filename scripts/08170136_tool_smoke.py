from __future__ import annotations

import argparse
import json
import time

from bio_mystery_synth.models import Backend, ExecutionSpec
from bio_mystery_synth.runtime import ProtoRuntime

GPU_TOOLS = ("esm2-score", "esm2-embedding", "esm2-sample", "esm2-gradient")
CPU_TOOLS = ("foldmason-msa", "foldmason-score-msa", "pyrosetta-energy", "pyrosetta-sasa")


def run(runtime: ProtoRuntime, tool: str, inputs: dict, config: dict) -> dict:
    started = time.monotonic()
    result = runtime.run_tool(tool, inputs, config)
    row = {
        "tool": tool,
        "device": runtime.calls[-1].device,
        "ok": runtime.calls[-1].ok,
        "success": result.get("success"),
        "seconds": round(time.monotonic() - started, 2),
    }
    print(json.dumps(row), flush=True)
    if not row["ok"] or not row["success"]:
        raise RuntimeError(f"{tool} smoke test failed")
    return result


def gpu_smoke() -> None:
    from proto_tools.tools import ToolRegistry
    from proto_tools.utils import ToolInstance

    runtime = ProtoRuntime(ExecutionSpec(backend=Backend.LOCAL, local_device="cuda:0"))
    with ToolInstance.persist_tool("esm2"):
        for tool in GPU_TOOLS:
            inputs = ToolRegistry.get_example_input(tool).model_dump(mode="json")
            run(runtime, tool, inputs, {"model_checkpoint": "esm2_t6_8M_UR50D", "batch_size": 2, "seed": 7})


def cpu_smoke() -> None:
    from proto_tools.tools import ToolRegistry

    runtime = ProtoRuntime(ExecutionSpec(backend=Backend.LOCAL, local_device="cpu"))
    msa_inputs = ToolRegistry.get_example_input("foldmason-msa").model_dump(mode="json")
    msa = run(runtime, "foldmason-msa", msa_inputs, {"search_mode": "local", "num_threads": 2})
    run(
        runtime,
        "foldmason-score-msa",
        {"structures": msa_inputs["structures"], "msa": msa["aa_msa_fasta"]},
        {"num_threads": 2},
    )
    run(runtime, "pyrosetta-energy", ToolRegistry.get_example_input("pyrosetta-energy").model_dump(mode="json"), {})
    run(runtime, "pyrosetta-sasa", ToolRegistry.get_example_input("pyrosetta-sasa").model_dump(mode="json"), {})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", choices=("cpu", "gpu"))
    args = parser.parse_args()
    (cpu_smoke if args.suite == "cpu" else gpu_smoke)()


if __name__ == "__main__":
    main()
