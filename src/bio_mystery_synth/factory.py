"""Default bounded scenarios."""

from __future__ import annotations

from bio_mystery_synth.models import (
    Backend,
    CrisprLinkageFamilySpec,
    Difficulty,
    DNAMotifFamilySpec,
    ExecutionSpec,
    ProteinBridgeFamilySpec,
    ProteinStructureFamilySpec,
    RecombinationFamilySpec,
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
            Difficulty.HARD: dict(num_sequences=96, sequence_length=20_000, num_targets=8, num_decoys=24),
        }[difficulty]
        family_spec = DNAMotifFamilySpec(**settings)
    elif family == "rna-structure-ranking":
        settings = {
            Difficulty.EASY: dict(num_candidates=5, sequence_length=80),
            Difficulty.MEDIUM: dict(num_candidates=8, sequence_length=120),
            Difficulty.HARD: dict(num_candidates=48, sequence_length=600),
        }[difficulty]
        family_spec = RNAStructureFamilySpec(**settings)
    elif family == "protein-structure-nearest":
        settings = {
            Difficulty.EASY: dict(num_candidates=4, sequence_length=90),
            Difficulty.MEDIUM: dict(num_candidates=6, sequence_length=140),
            Difficulty.HARD: dict(num_candidates=16, sequence_length=300),
        }[difficulty]
        family_spec = ProteinStructureFamilySpec(**settings)
    elif family == "protein-bridge-triage":
        settings = {
            Difficulty.EASY: dict(num_candidates=6, sequence_length=100, shortlist_size=3),
            Difficulty.MEDIUM: dict(num_candidates=8, sequence_length=140, shortlist_size=4),
            Difficulty.HARD: dict(num_candidates=8, sequence_length=180, shortlist_size=4),
        }[difficulty]
        family_spec = ProteinBridgeFamilySpec(**settings)
    elif family == "crispr-spacer-linkage":
        settings = {
            Difficulty.EASY: dict(num_genomes=8, genome_length=10_000, num_targets=1, num_decoys=2),
            Difficulty.MEDIUM: dict(num_genomes=24, genome_length=50_000, num_targets=3, num_decoys=6),
            Difficulty.HARD: dict(
                num_genomes=48,
                genome_length=100_000,
                phage_length=30_000,
                num_targets=4,
                num_decoys=12,
                num_repeats=10,
                linked_spacers=5,
            ),
        }[difficulty]
        family_spec = CrisprLinkageFamilySpec(**settings)
    elif family == "windowed-recombination":
        settings = {
            Difficulty.EASY: dict(num_candidates=12, sequence_length=1000, num_recombinants=1, window_size=100),
            Difficulty.MEDIUM: dict(num_candidates=48, sequence_length=4000, num_recombinants=3, window_size=200),
            Difficulty.HARD: dict(num_candidates=96, sequence_length=8000, num_recombinants=5, window_size=250),
        }[difficulty]
        family_spec = RecombinationFamilySpec(**settings)
    else:
        raise ValueError(f"unknown task family: {family}")
    return ScenarioSpec(
        difficulty=difficulty,
        seed=seed,
        family=family_spec,
        execution=execution,
    )
