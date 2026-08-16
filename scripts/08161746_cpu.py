"""Generate and audit the autonomous CPU case for experiment 08161746."""

from __future__ import annotations

import json
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, CaseIndexEntry, Difficulty, GenerationManifest
from bio_mystery_synth.pipeline import CaseGenerator, validate_case, write_index

SEED = 20260822
CASE_ID = "bms-autonomous-utr-assay-20260822"
TOOLS = {"orfipy-prediction", "miranda-scan", "viennarna-prediction", "primer3-thermodynamics"}


def main() -> None:
    root = Path(".")
    spec = default_scenario("utr-regulatory-assay", Difficulty.HARD, SEED, Backend.LOCAL, "cpu")
    generated = CaseGenerator(root).generate(spec, case_id=CASE_ID)
    errors = validate_case(generated.path)
    if errors:
        raise RuntimeError("; ".join(errors))
    manifest = GenerationManifest.model_validate_json(
        (generated.path / "private" / "generation_manifest.json").read_text()
    )
    observed = {call.tool for call in manifest.tool_calls}
    if not observed >= TOOLS or manifest.backend != Backend.LOCAL:
        raise RuntimeError("case did not record the required local tool chain")
    question = (generated.path / "public" / "question.md").read_text().lower()
    forbidden = TOOLS | {"orfipy", "miranda", "viennarna", "primer3", "score_threshold", "energy_threshold"}
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
