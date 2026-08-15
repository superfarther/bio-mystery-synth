"""Default bounded scenarios."""

from __future__ import annotations

from bio_mystery_synth.models import (
    Backend,
    Difficulty,
    DNAMotifFamilySpec,
    ExecutionSpec,
    ProteinStructureFamilySpec,
    RNAStructureFamilySpec,
    ScenarioSpec,
)


def default_scenario(
    family: str,
    difficulty: Difficulty,
    seed: int,
    backend: Backend,
    local_device: str = "cuda",
) -> ScenarioSpec:
    execution = ExecutionSpec(backend=backend, local_device=local_device)
    if family == "dna-motif-localization":
        settings = {
            Difficulty.EASY: dict(num_sequences=8, sequence_length=500, num_targets=1, num_decoys=2),
            Difficulty.MEDIUM: dict(num_sequences=16, sequence_length=1000, num_targets=2, num_decoys=3),
            Difficulty.HARD: dict(num_sequences=32, sequence_length=2000, num_targets=3, num_decoys=8),
        }[difficulty]
        family_spec = DNAMotifFamilySpec(**settings)
    elif family == "rna-structure-ranking":
        settings = {
            Difficulty.EASY: dict(num_candidates=5, sequence_length=80),
            Difficulty.MEDIUM: dict(num_candidates=8, sequence_length=120),
            Difficulty.HARD: dict(num_candidates=12, sequence_length=220),
        }[difficulty]
        family_spec = RNAStructureFamilySpec(**settings)
    elif family == "protein-structure-nearest":
        settings = {
            Difficulty.EASY: dict(num_candidates=4, sequence_length=90),
            Difficulty.MEDIUM: dict(num_candidates=6, sequence_length=140),
            Difficulty.HARD: dict(num_candidates=10, sequence_length=220),
        }[difficulty]
        family_spec = ProteinStructureFamilySpec(**settings)
    else:
        raise ValueError(f"unknown task family: {family}")
    return ScenarioSpec(
        difficulty=difficulty,
        seed=seed,
        family=family_spec,
        execution=execution,
    )
