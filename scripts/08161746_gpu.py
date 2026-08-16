"""Generate and audit the autonomous GPU case for experiment 08161746."""

from __future__ import annotations

import json
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, CaseIndexEntry, Difficulty, GenerationManifest
from bio_mystery_synth.pipeline import CaseGenerator, validate_case, write_index

SEED = 20260823
CASE_ID = "bms-autonomous-metagenomic-enzyme-20260823"
TOOLS = {
    "prodigal-prediction",
    "pyhmmer-phmmer",
    "esmfold-prediction",
    "structure-metrics",
    "tmalign-alignment",
}


def main() -> None:
    root = Path(".")
    spec = default_scenario("metagenomic-enzyme-forensics", Difficulty.HARD, SEED, Backend.LOCAL, "cuda")
    generated = CaseGenerator(root).generate(spec, case_id=CASE_ID)
    errors = validate_case(generated.path)
    if errors:
        raise RuntimeError("; ".join(errors))
    manifest = GenerationManifest.model_validate_json(
        (generated.path / "private" / "generation_manifest.json").read_text()
    )
    observed = {call.tool for call in manifest.tool_calls}
    gpu_calls = [call for call in manifest.tool_calls if call.tool == "esmfold-prediction"]
    if not observed >= TOOLS or manifest.backend != Backend.LOCAL or not gpu_calls:
        raise RuntimeError("case did not record the required local tool chain")
    if not all(call.ok and call.device.startswith("cuda") for call in gpu_calls):
        raise RuntimeError("ESMFold was not successfully executed on CUDA")
    question = (generated.path / "public" / "question.md").read_text().lower()
    forbidden = TOOLS | {
        "prodigal",
        "pyhmmer",
        "phmmer",
        "esmfold",
        "num_recycles",
        "max_batch_residues",
    }
    leaks = sorted(token for token in forbidden if token in question)
    if leaks:
        raise RuntimeError(f"question prescribes tools or parameters: {leaks}")
    entries = []
    index = root / "index.jsonl"
    if index.is_file():
        entries = [CaseIndexEntry.model_validate(json.loads(line)) for line in index.read_text().splitlines() if line]
    write_index(root, [entry for entry in entries if entry.case_id != CASE_ID] + [generated.index])
    print(generated.path)


if __name__ == "__main__":
    main()
