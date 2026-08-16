from typer.testing import CliRunner

from bio_mystery_synth.cli import app


def test_list_families() -> None:
    result = CliRunner().invoke(app, ["list-families"])
    assert result.exit_code == 0
    expected = {
        "dna-motif-localization",
        "protein-structure-nearest",
        "promoter-cassette-forensics",
        "profile-fold-rescue",
        "multimer-interface-selection",
        "conformation-ligand-triage",
        "mobile-element-attribution",
    }
    assert all(family in result.stdout for family in expected)


def test_list_tools() -> None:
    result = CliRunner().invoke(app, ["list-tools"])
    assert result.exit_code == 0
    assert "[profile-and-local-homology]" in result.stdout
    assert "39/39 tools available" in result.stdout
