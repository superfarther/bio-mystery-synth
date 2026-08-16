"""
Reproduce hard benchmark cases for experiment version 08160828.

This script pins case identifiers and random seeds to make the experiment reproducible.

Usage:
    python scripts/08160828.py <family>

Supported families:
    dna-motif-localization
    rna-structure-ranking
    crispr-spacer-linkage
    windowed-recombination
    protein-structure-nearest
"""

from __future__ import annotations

import argparse
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, Difficulty
from bio_mystery_synth.pipeline import CaseGenerator

CASES = {
    "dna-motif-localization": (20260816, "bms-hard-dna-motif-20260816"),
    "rna-structure-ranking": (20260817, "bms-hard-rna-structure-20260817"),
    "crispr-spacer-linkage": (20260818, "bms-hard-crispr-linkage-20260818"),
    "windowed-recombination": (20260819, "bms-hard-windowed-recombination-20260819"),
    "protein-structure-nearest": (20260820, "bms-hard-protein-structure-20260820"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=CASES)
    args = parser.parse_args()
    seed, case_id = CASES[args.family]
    device = "cuda" if args.family == "protein-structure-nearest" else "cpu"
    spec = default_scenario(args.family, Difficulty.HARD, seed, Backend.LOCAL, device)
    print(CaseGenerator(Path(".")).generate(spec, case_id=case_id).path)


if __name__ == "__main__":
    main()
