from __future__ import annotations

import math
import random

AA = "ACDEFGHIKLMNPQRSTVWY"


def mutate(sequence: str, count: int, rng: random.Random, protected: set[int] | None = None) -> str:
    protected = protected or set()
    positions = [index for index in range(1, len(sequence)) if index not in protected]
    chars = list(sequence)
    for position in rng.sample(positions, min(count, len(positions))):
        chars[position] = rng.choice(AA.replace(chars[position], ""))
    return "".join(chars)


def structure_text(value: dict[str, object]) -> str:
    structure = value.get("structure")
    if not isinstance(structure, str):
        raise RuntimeError("structure prediction returned no coordinates")
    return structure


def normalize(values: list[float], higher: bool = True) -> list[float]:
    low, high = min(values), max(values)
    scaled = [(value - low) / max(high - low, 1e-12) for value in values]
    return scaled if higher else [1 - value for value in scaled]


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return numerator / denominator


def parse_fasta(text: str) -> dict[str, str]:
    records: dict[str, str] = {}
    name = ""
    for line in text.splitlines():
        if line.startswith(">"):
            name = line[1:].split()[0]
            records[name] = ""
        elif name:
            records[name] += line.strip()
    return records


def aligned_identity(left: str, right: str) -> float:
    pairs = [(a, b) for a, b in zip(left, right, strict=True) if a != "-" and b != "-"]
    return sum(a == b for a, b in pairs) / len(pairs)


def one_hot_logits(sequence: str, sharpness: float = 2.0) -> list[list[float]]:
    return [[sharpness if residue == aa else -sharpness for aa in AA] for residue in sequence]
