import json
import shutil
from pathlib import Path

from bio_mystery_synth.core import CaseIndexEntry


def write_index(output_root: Path, entries: list[CaseIndexEntry]) -> Path:
    path = output_root / "index.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(entry.model_dump(mode="json"), sort_keys=True) + "\n" for entry in entries)
    path.write_text(text)
    return path


def clean_staging(output_root: Path) -> None:
    stage = output_root / ".staging"
    if stage.exists() and not any(stage.iterdir()):
        shutil.rmtree(stage)
