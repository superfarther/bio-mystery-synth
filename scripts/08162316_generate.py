"""Generate and audit the five long-horizon cases for run 08162316."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, CaseIndexEntry, Difficulty, GenerationManifest
from bio_mystery_synth.pipeline import CaseGenerator, validate_case, write_index

JOBS = {
    "promoter-cassette-forensics": (
        2026081601,
        "bms-promoter-cassette-forensics-2026081601",
        {"prodigal-prediction", "pyhmmer-jackhmmer", "pyhmmer-nhmmer", "promoter-calculator"},
    ),
    "profile-fold-rescue": (
        2026081602,
        "bms-profile-fold-rescue-2026081602",
        {
            "mafft-align",
            "pyhmmer-hmmsearch",
            "esmfold-prediction",
            "foldseek-cluster",
            "dssp-secondary-structure",
            "usalign-alignment",
        },
    ),
    "multimer-interface-selection": (
        2026081603,
        "bms-multimer-interface-selection-2026081603",
        {
            "mmseqs2-clustering",
            "esmfold-prediction",
            "foldseek-multimercluster",
            "ipsae-scoring",
            "pdockq2",
        },
    ),
    "conformation-ligand-triage": (
        2026081604,
        "bms-conformation-ligand-triage-2026081604",
        {
            "esmfold-prediction",
            "usalign-alignment",
            "pymol-rmsd-alignment",
            "dssp-secondary-structure",
            "vina-docking",
        },
    ),
    "mobile-element-attribution": (
        2026081605,
        "bms-mobile-element-attribution-2026081605",
        {
            "mmseqs2-search-genomes",
            "pyhmmer-nhmmer",
            "blast-create-db",
            "blast-search",
            "prodigal-prediction",
        },
    ),
}

FORBIDDEN = {
    "blast",
    "dssp",
    "esmfold",
    "foldseek",
    "ipsae",
    "jackhmmer",
    "mafft",
    "mmseqs",
    "nhmmer",
    "pdockq",
    "prodigal",
    "promoter calculator",
    "pyhmmer",
    "pymol",
    "usalign",
    "vina",
    "exhaustiveness",
    "max_batch_residues",
    "num_recycles",
}


def audit(path: Path, tools: set[str]) -> GenerationManifest:
    errors = validate_case(path)
    if errors:
        raise RuntimeError("; ".join(errors))
    manifest = GenerationManifest.model_validate_json((path / "private/generation_manifest.json").read_text())
    observed = {call.tool for call in manifest.tool_calls}
    if manifest.backend != Backend.LOCAL or not observed >= tools or not all(call.ok for call in manifest.tool_calls):
        raise RuntimeError(f"incomplete local tool chain: expected={sorted(tools)}, observed={sorted(observed)}")
    gpu_calls = [call for call in manifest.tool_calls if call.tool == "esmfold-prediction"]
    if "esmfold-prediction" in tools and not gpu_calls:
        raise RuntimeError("missing ESMFold GPU call")
    if gpu_calls and not all(call.device.startswith("cuda") for call in gpu_calls):
        raise RuntimeError("ESMFold did not execute on CUDA")
    question = (path / "public/question.md").read_text().lower()
    leaks = sorted(token for token in FORBIDDEN if token in question)
    if leaks:
        raise RuntimeError(f"question prescribes tools or parameters: {leaks}")
    return manifest


def update_index(root: Path, entry: CaseIndexEntry) -> None:
    index = root / "index.jsonl"
    entries = [
        CaseIndexEntry.model_validate(json.loads(line))
        for line in index.read_text().splitlines()
        if line
    ] if index.is_file() else []
    write_index(root, [item for item in entries if item.case_id != entry.case_id] + [entry])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=sorted(JOBS))
    args = parser.parse_args()
    family = args.family
    seed, case_id, tools = JOBS[family]
    root = Path(".").resolve()
    spec = default_scenario(family, Difficulty.HARD, seed, Backend.LOCAL, "cuda")
    generated = CaseGenerator(root).generate(spec, case_id=case_id)
    manifest = audit(generated.path, tools)
    update_index(root, generated.index)
    print(json.dumps({"case": str(generated.path), "calls": len(manifest.tool_calls)}))


if __name__ == "__main__":
    main()
