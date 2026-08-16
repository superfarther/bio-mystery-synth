"""Reproduce and audit the long-horizon GPU case for experiment 08160943."""

from __future__ import annotations

import json
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, CaseIndexEntry, Difficulty, GenerationManifest
from bio_mystery_synth.pipeline import CaseGenerator, validate_case, write_index

SEED = 20260821
CASE_ID = "bms-long-protein-bridge-20260821"


def main() -> None:
    root = Path(".")
    spec = default_scenario("protein-bridge-triage", Difficulty.HARD, SEED, Backend.LOCAL, "cuda")
    generated = CaseGenerator(root).generate(spec, case_id=CASE_ID)
    errors = validate_case(generated.path)
    if errors:
        raise RuntimeError("; ".join(errors))
    manifest = GenerationManifest.model_validate_json(
        (generated.path / "private" / "generation_manifest.json").read_text()
    )
    if len(manifest.tool_calls) < 9 or not any(call.device.startswith("cuda") for call in manifest.tool_calls):
        raise RuntimeError("case did not record the required long-horizon GPU tool chain")
    entries = []
    index = root / "index.jsonl"
    if index.is_file():
        entries = [CaseIndexEntry.model_validate(json.loads(line)) for line in index.read_text().splitlines() if line]
    write_index(root, [entry for entry in entries if entry.case_id != CASE_ID] + [generated.index])
    print(generated.path)


if __name__ == "__main__":
    main()
