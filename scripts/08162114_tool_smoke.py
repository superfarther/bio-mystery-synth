from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from bio_mystery_synth.models import Backend, ExecutionSpec
from bio_mystery_synth.runtime import ProtoRuntime

GENERIC_TOOLS = (
    "promoter-calculator",
    "pyhmmer-hmmscan",
    "pyhmmer-hmmsearch",
    "pyhmmer-jackhmmer",
    "pyhmmer-nhmmer",
    "foldseek-cluster",
    "foldseek-multimercluster",
    "pymol-rmsd-alignment",
    "usalign-alignment",
    "dssp-secondary-structure",
    "vina-docking",
    "ipsae-scoring",
    "pdockq2",
)

CONFIGS = {
    "foldseek-cluster": {"num_threads": 2, "timeout": 60},
    "foldseek-multimercluster": {"num_threads": 2, "timeout": 60},
    "vina-docking": {"cpu": 1, "exhaustiveness": 1, "num_poses": 1, "seed": 7},
}


def run(runtime: ProtoRuntime, key: str, input_data: dict, config: dict | None = None) -> None:
    started = time.monotonic()
    result = runtime.run_tool(key, input_data, config or {})
    print(
        json.dumps(
            {
                "tool": key,
                "ok": runtime.calls[-1].ok,
                "success": result.get("success"),
                "seconds": round(time.monotonic() - started, 2),
            }
        ),
        flush=True,
    )


def main() -> None:
    from proto_tools.tools import ToolRegistry

    runtime = ProtoRuntime(ExecutionSpec(backend=Backend.LOCAL, local_device="cpu"))
    registry = ToolRegistry

    for key in GENERIC_TOOLS:
        run(runtime, key, registry.get_example_input(key).model_dump(), CONFIGS.get(key))

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "target.fasta"
        query = root / "query.fasta"
        target.write_text(">target\nACGTACGTACGTACGTACGTACGTACGT\n")
        query.write_text(">query\nACGTACGTACGTACGT\n")
        prefix = root / "blastdb"
        run(
            runtime,
            "blast-create-db",
            {"fasta": str(target)},
            {"dbtype": "nucl", "out_prefix": str(prefix)},
        )
        run(
            runtime,
            "blast-search",
            {"query": str(query)},
            {"local_db": str(prefix), "program": "blastn", "word_size": 7},
        )

    run(
        runtime,
        "mmseqs2-clustering",
        registry.get_example_input("mmseqs2-clustering").model_dump(),
        {"timeout": 60, "extra_args": ["--threads", "2"]},
    )
    run(
        runtime,
        "mmseqs2-search-genomes",
        registry.get_example_input("mmseqs2-search-genomes").model_dump(),
        {"target_genomes": ["ATCGATCG"], "threads": 2, "min_seq_id": 0.5, "timeout": 60},
    )


if __name__ == "__main__":
    main()
