"""Small deterministic helpers."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from bio_mystery_synth.models import AnonymizationSpec, AnswerSpec


def anonymize(raw_ids: list[str], spec: AnonymizationSpec, rng: random.Random) -> dict[str, str]:
    names = [f"{spec.sample_prefix}_{i:0{spec.width}d}" for i in range(1, len(raw_ids) + 1)]
    if spec.shuffle:
        rng.shuffle(names)
    return dict(zip(raw_ids, names, strict=True))


def fasta(records: list[tuple[str, str]]) -> str:
    return "".join(f">{name}\n{sequence}\n" for name, sequence in records)


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def base_pairs(structure: str) -> set[tuple[int, int]]:
    stack: list[int] = []
    pairs: set[tuple[int, int]] = set()
    for index, symbol in enumerate(structure):
        if symbol == "(":
            stack.append(index)
        elif symbol == ")" and stack:
            pairs.add((stack.pop(), index))
    return pairs


def jaccard(left: set[Any], right: set[Any]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def render_answer(answer: AnswerSpec) -> str:
    lines = ["# Grading rubric", "", answer.rubric_text, "", "## Machine assertions", ""]
    for assertion in answer.assertions:
        lines.append(f"- `{assertion.kind}` on `{assertion.field}`")
    return "\n".join(lines) + "\n"


def dump_json(value: Any) -> str:
    if isinstance(value, BaseException):
        value = {"error": str(value)}
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
