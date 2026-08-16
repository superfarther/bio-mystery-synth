from __future__ import annotations

import json
from functools import reduce
from operator import or_
from typing import Annotated

from pydantic import Field, create_model

from bio_mystery_synth.authoring.clients import LLMClient
from bio_mystery_synth.core import ScenarioSpec, StrictModel
from bio_mystery_synth.runtime import capability_catalog
from bio_mystery_synth.task_families.registry import family_definitions


class ScenarioEnvelope(StrictModel):
    scenario: ScenarioSpec


def _planning_envelope() -> type[StrictModel]:
    config_models = [definition.config_model for definition in family_definitions().values()]
    family_union = reduce(or_, config_models)
    family_field = Annotated[family_union, Field(discriminator="kind")]
    planned = create_model("PlannedScenarioSpec", __base__=ScenarioSpec, family=(family_field, ...))
    return create_model("PlannedScenarioEnvelope", __base__=StrictModel, scenario=(planned, ...))


class ScenarioPlanner:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def plan(self, request: str) -> ScenarioSpec:
        catalog = json.dumps(capability_catalog(), sort_keys=True)
        result = self.client.generate(
            _planning_envelope(),
            "Plan one closed-world bioinformatics case. Use only the supplied catalog and emit the requested schema.",
            f"Request:\n{request}\nCapability catalog:\n{catalog}",
        )
        return ScenarioSpec.model_validate(result.scenario.model_dump())
