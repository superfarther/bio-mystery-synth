from pathlib import Path

import pytest
from conftest import FakeRuntime

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, Difficulty
from bio_mystery_synth.pipeline import CaseGenerator, validate_case


@pytest.mark.parametrize(
    "family",
    [
        "dna-motif-localization",
        "rna-structure-ranking",
        "protein-structure-nearest",
        "protein-bridge-triage",
        "crispr-spacer-linkage",
        "windowed-recombination",
    ],
)
def test_family_end_to_end(tmp_path: Path, family: str) -> None:
    scenario = default_scenario(family, Difficulty.EASY, 42, Backend.LOCAL, "cpu")
    generated = CaseGenerator(tmp_path).generate(scenario, runtime=FakeRuntime(42), case_id=f"case-{family}")
    assert validate_case(generated.path) == []
    assert (generated.path / "public" / "question.md").is_file()
    assert (generated.path / "private" / "answer.json").is_file()


def test_public_tree_does_not_contain_raw_ids(tmp_path: Path) -> None:
    scenario = default_scenario("dna-motif-localization", Difficulty.EASY, 7, Backend.LOCAL, "cpu")
    generated = CaseGenerator(tmp_path).generate(scenario, runtime=FakeRuntime(7), case_id="case-no-leak")
    public = "\n".join(path.read_text() for path in (generated.path / "public").rglob("*") if path.is_file())
    assert "dna_001" not in public


def test_validation_detects_public_leak(tmp_path: Path) -> None:
    scenario = default_scenario("dna-motif-localization", Difficulty.EASY, 9, Backend.LOCAL, "cpu")
    generated = CaseGenerator(tmp_path).generate(scenario, runtime=FakeRuntime(9), case_id="case-leak")
    question = generated.path / "public" / "question.md"
    question.write_text(question.read_text() + "\ndna_001\n")
    errors = validate_case(generated.path)
    assert any("leaks dna_001" in error for error in errors)
    assert any("hash mismatch" in error for error in errors)
