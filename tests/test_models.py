from pydantic import ValidationError

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.models import Backend, Difficulty, ScenarioSpec


def test_scenario_round_trip() -> None:
    scenario = default_scenario("dna-motif-localization", Difficulty.MEDIUM, 42, Backend.LOCAL, "cpu")
    restored = ScenarioSpec.model_validate_json(scenario.model_dump_json())
    assert restored == scenario
    assert restored.task_family == "dna-motif-localization"


def test_unknown_fields_are_rejected() -> None:
    scenario = default_scenario("rna-structure-ranking", Difficulty.EASY, 4, Backend.LOCAL, "cpu")
    payload = scenario.model_dump()
    payload["unknown"] = True
    try:
        ScenarioSpec.model_validate(payload)
    except ValidationError:
        return
    raise AssertionError("unknown field was accepted")
