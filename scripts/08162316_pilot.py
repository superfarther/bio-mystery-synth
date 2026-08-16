"""Run a disposable easy-scale real-runtime pilot for a new family."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, Difficulty
from bio_mystery_synth.pipeline import CaseGenerator, validate_case


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("family")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix=f"bms-pilot-{args.family}-", dir="/tmp"))
    spec = default_scenario(args.family, Difficulty.EASY, 8162400, Backend.LOCAL, "cuda")
    generated = CaseGenerator(root).generate(spec, case_id=f"pilot-{args.family}")
    errors = validate_case(generated.path)
    if errors:
        raise RuntimeError("; ".join(errors))
    print(generated.path)


if __name__ == "__main__":
    main()
