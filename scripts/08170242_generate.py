"""Generate and audit three high-volume long-horizon cases for run 08170242."""

from __future__ import annotations

import argparse
import json
from contextlib import nullcontext
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, CaseIndexEntry, Difficulty, GenerationManifest
from bio_mystery_synth.pipeline import CaseGenerator, validate_case, write_index

BASELINE_PUBLIC_BYTES = 1_623_757
JOBS = {
    "protein-repair-adjudication": (
        2026081701,
        "bms-protein-repair-adjudication-2026081701",
        {
            "esm2-gradient",
            "esm2-sample",
            "esm2-score",
            "esm2-embedding",
            "esmfold-prediction",
            "usalign-alignment",
            "dssp-secondary-structure",
            "pyrosetta-energy",
            "pyrosetta-sasa",
        },
    ),
    "structural-discordance-cohort": (
        2026081702,
        "bms-structural-discordance-cohort-2026081702",
        {
            "esmfold-prediction",
            "mafft-align",
            "foldmason-msa",
            "foldmason-score-msa",
            "foldseek-cluster",
            "usalign-alignment",
            "dssp-secondary-structure",
            "pyrosetta-energy",
            "pyrosetta-sasa",
        },
    ),
    "metagenomic-stability-forensics": (
        2026081703,
        "bms-metagenomic-stability-forensics-2026081703",
        {
            "prodigal-prediction",
            "pyhmmer-phmmer",
            "esm2-score",
            "esm2-embedding",
            "esmfold-prediction",
            "foldmason-msa",
            "foldmason-score-msa",
            "foldseek-cluster",
            "usalign-alignment",
            "dssp-secondary-structure",
            "pyrosetta-energy",
            "pyrosetta-sasa",
        },
    ),
}
FORBIDDEN = {
    "blast",
    "dssp",
    "esm2",
    "esmfold",
    "foldmason",
    "foldseek",
    "mafft",
    "mmseqs",
    "prodigal",
    "pyhmmer",
    "pyrosetta",
    "usalign",
    "batch_size",
    "model_checkpoint",
    "num_recycles",
    "num_threads",
    "search_mode",
}


def audit(path: Path, expected_tools: set[str]) -> GenerationManifest:
    errors = validate_case(path)
    if errors:
        raise RuntimeError("; ".join(errors))
    manifest = GenerationManifest.model_validate_json((path / "private/generation_manifest.json").read_text())
    observed = {call.tool for call in manifest.tool_calls}
    if (
        manifest.backend != Backend.LOCAL
        or not observed >= expected_tools
        or not all(call.ok for call in manifest.tool_calls)
    ):
        raise RuntimeError(f"incomplete local chain: expected={sorted(expected_tools)}, observed={sorted(observed)}")
    gpu = [
        call
        for call in manifest.tool_calls
        if call.tool in {"esm2-gradient", "esm2-sample", "esm2-score", "esm2-embedding", "esmfold-prediction"}
    ]
    if not gpu or not all(call.device.startswith("cuda") for call in gpu):
        raise RuntimeError("GPU tools did not all execute on CUDA")
    public_bytes = sum(item.stat().st_size for item in (path / "public").rglob("*") if item.is_file())
    if public_bytes <= BASELINE_PUBLIC_BYTES:
        raise RuntimeError(f"public data did not exceed baseline: {public_bytes} <= {BASELINE_PUBLIC_BYTES}")
    question = (path / "public/question.md").read_text().lower()
    leaks = sorted(token for token in FORBIDDEN if token in question)
    if leaks:
        raise RuntimeError(f"question exposes tools or execution parameters: {leaks}")
    return manifest


def update_index(root: Path, entry: CaseIndexEntry) -> None:
    index = root / "index.jsonl"
    entries = [CaseIndexEntry.model_validate(json.loads(line)) for line in index.read_text().splitlines() if line]
    write_index(root, [item for item in entries if item.case_id != entry.case_id] + [entry])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=sorted(JOBS))
    args = parser.parse_args()
    seed, case_id, tools = JOBS[args.family]
    root = Path(".").resolve()
    spec = default_scenario(args.family, Difficulty.HARD, seed, Backend.LOCAL, "cuda:0")
    if tools & {"esm2-gradient", "esm2-sample", "esm2-score", "esm2-embedding"}:
        from proto_tools.utils import ToolInstance

        persistent = ToolInstance.persist_tool("esm2")
    else:
        persistent = nullcontext()
    with persistent:
        generated = CaseGenerator(root).generate(spec, case_id=case_id)
    manifest = audit(generated.path, tools)
    update_index(root, generated.index)
    public_bytes = sum(item.stat().st_size for item in (generated.path / "public").rglob("*") if item.is_file())
    print(json.dumps({"case": str(generated.path), "calls": len(manifest.tool_calls), "public_bytes": public_bytes}))


if __name__ == "__main__":
    main()
