from typing import Any


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTUacgtu", "TGCAAtgcaa"))[::-1]


def base_pairs(structure: str) -> set[tuple[int, int]]:
    stack: list[int] = []
    pairs: set[tuple[int, int]] = set()
    for index, token in enumerate(structure):
        if token == "(":
            stack.append(index)
        elif token == ")" and stack:
            pairs.add((stack.pop(), index))
    return pairs


def jaccard(left: set[Any], right: set[Any]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0
