from bio_mystery_synth.core import Backend, Difficulty, ExecutionSpec, ScenarioSpec
from bio_mystery_synth.task_families.registry import get_family_definition


def default_scenario(
    family: str,
    difficulty: Difficulty,
    seed: int,
    backend: Backend,
    local_device: str = "cuda",
) -> ScenarioSpec:
    definition = get_family_definition(family)
    return ScenarioSpec(
        difficulty=difficulty,
        seed=seed,
        family=definition.create_config(difficulty),
        execution=ExecutionSpec(backend=backend, local_device=local_device),
    )
