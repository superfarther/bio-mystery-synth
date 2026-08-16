"""Profile-guided remote homolog rescue with structural adjudication."""

from __future__ import annotations

import random
import re
from pathlib import Path

from bio_mystery_synth.biology import fasta
from bio_mystery_synth.core import (
    AnswerSpec,
    Difficulty,
    ExactAssertion,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    ScenarioSpec,
    SetAssertion,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import ProfileFoldFamilySpec

_REFERENCE = "MRKKLDLKKFVEDKNQEYAARALGLSQKLIEEVLKRGLPVYVETNKDGNIKVYITQDGITQPFPP"
_AA = "ACDEFGHIKLMNPQRSTVWY"


def _mutate(sequence: str, count: int, rng: random.Random) -> str:
    chars = list(sequence)
    for position in rng.sample(range(len(chars)), min(count, len(chars))):
        chars[position] = rng.choice(_AA.replace(chars[position], ""))
    return "".join(chars)


def _write_hmm(path: Path, ids: list[str], aligned: list[str]) -> str:
    import pyhmmer

    alphabet = pyhmmer.easel.Alphabet.amino()
    msa = pyhmmer.easel.TextMSA(
        name=b"Synthetic_fold_family",
        sequences=[
            pyhmmer.easel.TextSequence(name=name.encode(), sequence=sequence)
            for name, sequence in zip(ids, aligned, strict=True)
        ],
    ).digitize(alphabet)
    hmm, _, _ = pyhmmer.plan7.Builder(alphabet).build_msa(msa, pyhmmer.plan7.Background(alphabet))
    with path.open("wb") as handle:
        hmm.write(handle)
    return path.read_text()


def _target_index(name: str) -> int | None:
    match = re.search(r"(\d+)$", name)
    return int(match.group(1)) if match else None


@register
class ProfileFoldFamily:
    family_id = "profile-fold-rescue"
    config_model = ProfileFoldFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_candidates=8, shortlist_size=4),
        Difficulty.MEDIUM: dict(num_candidates=10, shortlist_size=5),
        Difficulty.HARD: dict(num_candidates=14, shortlist_size=7),
    }
    tools = (
        "mafft-align",
        "pyhmmer-hmmsearch",
        "esmfold-prediction",
        "foldseek-cluster",
        "dssp-secondary-structure",
        "usalign-alignment",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, ProfileFoldFamilySpec):
            raise TypeError("invalid profile fold family spec")
        rng = random.Random(spec.seed)
        training = [_REFERENCE, _mutate(_REFERENCE, 7, rng), _mutate(_REFERENCE, 13, rng)]
        candidates = [
            _mutate(_REFERENCE, round(8 + index * 35 / max(1, config.num_candidates - 1)), rng)
            for index in range(config.num_candidates)
        ]
        candidates[-2] = candidates[-2][len(candidates[-2]) // 2 :] + candidates[-2][: len(candidates[-2]) // 2]
        candidates[-1] = candidates[-1][:28] + "GPGPGPGPGPGP" + candidates[-1][40:]
        raw_ids = [f"fold_candidate_{index:03d}" for index in range(1, config.num_candidates + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)

        alignment = runtime.run_tool(
            "mafft-align",
            {"sequences": training, "sequence_ids": ["Seed_A", "Seed_B", "Seed_C"]},
            {"align_method": "auto", "max_iterations": 100, "threads": 2},
        )["msa"]
        hmm_path = context.workspace / "synthetic_fold_family.hmm"
        hmm_text = _write_hmm(hmm_path, alignment["sequence_ids"], alignment["aligned_sequences"])
        profile = runtime.run_tool(
            "pyhmmer-hmmsearch",
            {"sequences": candidates, "hmm": str(hmm_path)},
            {"evalue_threshold": 10.0, "domain_evalue_threshold": 10.0, "num_threads": 4},
        )
        profile_scores: dict[int, float] = {}
        for hit in profile["sequence_hits"]:
            index = _target_index(str(hit["target_name"]))
            if index is not None and index < config.num_candidates:
                profile_scores[index] = max(profile_scores.get(index, float("-inf")), float(hit["score"]))
        ordered = sorted(
            range(config.num_candidates),
            key=lambda index: (-profile_scores.get(index, float("-inf")), index),
        )
        shortlist_indexes = ordered[: config.shortlist_size]
        if any(index not in profile_scores for index in shortlist_indexes):
            raise RuntimeError("profile search did not recover a complete shortlist")

        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [_REFERENCE, *(candidates[index] for index in shortlist_indexes)]},
            {"num_recycles": 4, "max_batch_residues": 1200},
        )["structures"]
        structures = [item["structure"] for item in predicted]
        structure_ids = ["Reference", *(mapping[raw_ids[index]] for index in shortlist_indexes)]
        clusters = runtime.run_tool(
            "foldseek-cluster",
            {"structures": structures, "structure_ids": structure_ids},
            {
                "cov": 0.7,
                "alignment_type": 1,
                "tmscore_threshold": 0.35,
                "num_threads": 4,
            },
        )
        secondary = runtime.run_tool(
            "dssp-secondary-structure",
            {"inputs": structures},
            {},
        )["results"]
        reference_ss = secondary[0]
        tm_scores: dict[int, float] = {}
        for position, index in enumerate(shortlist_indexes, start=1):
            aligned = runtime.run_tool(
                "usalign-alignment",
                {"query_structure": structures[position], "reference_structure": structures[0]},
                {},
            )
            tm_scores[index] = float(aligned["metrics"]["tm_score_structure_2"])
        values = [profile_scores[index] for index in shortlist_indexes]
        low, high = min(values), max(values)
        normalized = {index: (profile_scores[index] - low) / max(high - low, 1e-9) for index in shortlist_indexes}
        scores: dict[int, float] = {}
        for position, index in enumerate(shortlist_indexes, start=1):
            ss_distance = sum(
                abs(float(secondary[position][field]) - float(reference_ss[field]))
                for field in ("helix_pct", "sheet_pct", "loop_pct")
            ) / 200
            confidence = float(predicted[position]["metrics"]["avg_plddt"])
            scores[index] = (
                0.55 * tm_scores[index]
                + 0.25 * confidence
                + 0.1 * normalized[index]
                + 0.1 * (1 - ss_distance)
            )
        ranking = sorted(shortlist_indexes, key=lambda index: (-scores[index], mapping[raw_ids[index]]))
        winner = ranking[0]
        winner_id = mapping[raw_ids[winner]]
        shortlist_ids = [mapping[raw_ids[index]] for index in shortlist_indexes]

        public_files = {
            "data/candidates.fasta": fasta(
                sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, candidates, strict=True))
            ),
            "data/profile_seeds.fasta": fasta(list(zip(["Seed_A", "Seed_B", "Seed_C"], training, strict=True))),
            "data/family_profile.hmm": hmm_text,
            "data/reference_fold.pdb": structures[0],
        }
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "candidate_sequences": dict(zip(raw_ids, candidates, strict=True)),
                    "profile_scores": {mapping[raw_ids[index]]: value for index, value in profile_scores.items()},
                    "shortlist": shortlist_ids,
                    "structure_ids": structure_ids,
                    "tm_scores": {mapping[raw_ids[index]]: value for index, value in tm_scores.items()},
                    "secondary_structure": dict(zip(structure_ids, secondary, strict=True)),
                    "final_scores": {mapping[raw_ids[index]]: value for index, value in scores.items()},
                    "winner": winner_id,
                },
                anonymization_map=mapping,
                evidence={"profile_search": profile, "structure_clusters": clusters, "predictions": predicted},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    SetAssertion(field="shortlist", expected=shortlist_ids),
                    ExactAssertion(field="winner", expected=winner_id),
                ],
                rubric_text=f"Credit requires shortlist {', '.join(shortlist_ids)} and winner {winner_id}.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Rescue a remote homolog by reconciling profile and fold evidence",
                public_files=sorted(public_files),
                answer_format="shortlist: Sample_..., ...\nwinner: Sample_...",
                default_question=(
                    "Use the closed candidate collection in `data/candidates.fasta`, the seed alignment material "
                    "in `data/profile_seeds.fasta`, its supplied family profile in `data/family_profile.hmm`, and "
                    "the reference structure in `data/reference_fold.pdb`. First identify the strongest profile-"
                    f"supported remote relatives, retaining {config.shortlist_size} candidates. Among that set, "
                    "identify the single "
                    "candidate whose predicted fold most convincingly preserves the reference topology and "
                    "secondary-structure composition while remaining well resolved. Report the "
                    f"{config.shortlist_size}-member shortlist and the final winner. The final call must integrate "
                    "sequence-profile, global fold, "
                    "structural clustering, confidence, and secondary-structure evidence."
                ),
            ),
        )


PROFILE_FOLD_FAMILY = ProfileFoldFamily()
