from typer.testing import CliRunner

from bio_mystery_synth.cli import app


def test_list_families() -> None:
    result = CliRunner().invoke(app, ["list-families"])
    assert result.exit_code == 0
    assert "dna-motif-localization" in result.stdout
    assert "protein-structure-nearest" in result.stdout
