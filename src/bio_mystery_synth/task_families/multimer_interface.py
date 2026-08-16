"""Sequence-diverse binder selection by cofolded interface evidence."""

from __future__ import annotations

import random

from bio_mystery_synth.biology import fasta
from bio_mystery_synth.core import (
    AnswerSpec,
    Difficulty,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    RankingAssertion,
    ScenarioSpec,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import MultimerInterfaceFamilySpec

_TARGET = "PQITLWQRPLVTIKIGGQLKEALLDTGADDTVLEEMSLPGRWKPKMIGGIGGFIKVRQYDQILIEICGHKAIGTVLVGPTPVNIIGRNLLTQIGCTLNF"
_AA = "ACDEFGHIKLMNPQRSTVWY"


def _mutate(sequence: str, count: int, rng: random.Random) -> str:
    chars = list(sequence)
    for position in rng.sample(range(len(chars)), min(count, len(chars))):
        chars[position] = rng.choice(_AA.replace(chars[position], ""))
    return "".join(chars)


def _without_linker_pae(structure: dict[str, object], chain_length: int, linker_length: int = 25) -> dict[str, object]:
    metrics = dict(structure["metrics"])
    pae = metrics["pae"]
    keep = [*range(chain_length), *range(chain_length + linker_length, 2 * chain_length + linker_length)]
    metrics["pae"] = [[pae[row][column] for column in keep] for row in keep]
    return {**structure, "metrics": metrics}


@register
class MultimerInterfaceFamily:
    family_id = "multimer-interface-selection"
    config_model = MultimerInterfaceFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_binders=6, mutation_fraction=0.18),
        Difficulty.MEDIUM: dict(num_binders=8, mutation_fraction=0.24),
        Difficulty.HARD: dict(num_binders=12, mutation_fraction=0.34),
    }
    tools = (
        "mmseqs2-clustering",
        "esmfold-prediction",
        "foldseek-multimercluster",
        "ipsae-scoring",
        "pdockq2",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, MultimerInterfaceFamilySpec):
            raise TypeError("invalid multimer interface family spec")
        rng = random.Random(spec.seed)
        binders = [
            _mutate(
                _TARGET,
                round(len(_TARGET) * config.mutation_fraction * (0.25 + index / max(1, config.num_binders - 1))),
                rng,
            )
            for index in range(config.num_binders)
        ]
        binders[-2] = binders[-2][:45] + "GPGPGPGPGP" + binders[-2][55:]
        binders[-1] = binders[-1][len(binders[-1]) // 2 :] + binders[-1][: len(binders[-1]) // 2]
        raw_ids = [f"binder_{index:03d}" for index in range(1, config.num_binders + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        sample_ids = [mapping[raw] for raw in raw_ids]
        sequence_clusters = runtime.run_tool(
            "mmseqs2-clustering",
            {"input_sequences": binders, "sequence_ids": sample_ids},
            {
                "min_seq_id": 0.55,
                "coverage": 0.8,
                "cluster_mode": 0,
                "timeout": 180,
                "extra_args": ["--threads", "4"],
            },
        )
        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [[_TARGET, binder] for binder in binders]},
            {"num_recycles": 6, "max_batch_residues": 1400, "include_pae_matrix": True},
        )["structures"]
        scored_structures = [_without_linker_pae(item, len(_TARGET)) for item in predicted]
        structures = [item["structure"] for item in scored_structures]
        multimer_clusters = runtime.run_tool(
            "foldseek-multimercluster",
            {"structures": structures, "structure_ids": [sample.replace("_", "-") for sample in sample_ids]},
            {
                "multimer_tm_threshold": 0.55,
                "chain_tm_threshold": 0.2,
                "interface_lddt_threshold": 0.35,
                "num_threads": 4,
            },
        )
        interface: dict[str, dict[str, object]] = {}
        scores: dict[str, float] = {}
        for sample, structure in zip(sample_ids, scored_structures, strict=True):
            selection = {"binder_chain": {"chain": "B"}, "target_chains": {"chains": ["A"]}}
            ipsae = runtime.run_tool("ipsae-scoring", {"structure": structure, **selection}, {})
            pdockq = runtime.run_tool("pdockq2", {"structure": structure, **selection}, {})
            interface[sample] = {"ipsae": ipsae, "pdockq2": pdockq}
            scores[sample] = (
                0.45 * float(ipsae["metrics"]["ipsae"])
                + 0.35 * float(pdockq["metrics"]["pdockq2"])
                + 0.2 * float(structure["metrics"]["avg_plddt"])
            )
        ranking = sorted(sample_ids, key=lambda sample: (-scores[sample], sample))
        top_three = ranking[:3]

        public_files = {
            "data/target.fasta": fasta([("Synthetic_target", _TARGET)]),
            "data/binders.fasta": fasta(sorted(zip(sample_ids, binders, strict=True))),
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "raw_binders": dict(zip(raw_ids, binders, strict=True)),
                    "sequence_clusters": sequence_clusters,
                    "multimer_clusters": multimer_clusters,
                    "interface_scores": interface,
                    "composite_scores": scores,
                    "ranking": ranking,
                    "top_three": top_three,
                },
                anonymization_map=mapping,
                evidence={"cofolded_predictions": scored_structures},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[RankingAssertion(field="top_three", expected=top_three)],
                rubric_text="Credit requires the top three binders in order: " + " > ".join(top_three),
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Prioritize sequence-diverse binders by coherent multimer interface evidence",
                public_files=sorted(public_files),
                answer_format="top_three: Sample_... > Sample_... > Sample_...",
                default_question=(
                    "`data/binders.fasta` contains a diverse synthetic binder panel for the protein in "
                    "`data/target.fasta`. Rank the three most credible binders. A defensible ranking must account "
                    "for sequence redundancy, the geometry of predicted two-chain assemblies, uncertainty both "
                    "within and across the interface, local contact density, and overall model confidence. Treat "
                    "apparent contacts unsupported by cross-chain confidence as decoys, and do not let a single "
                    "headline score override contradictory interface evidence."
                ),
            ),
        )


MULTIMER_INTERFACE_FAMILY = MultimerInterfaceFamily()
