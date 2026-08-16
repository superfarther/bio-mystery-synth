"""Receptor-conformation and ligand triage with structural and docking evidence."""

from __future__ import annotations

import random

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
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.privacy import anonymize
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.task_families.specs import ConformationLigandFamilySpec

_RECEPTOR = (
    "MDPSSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYL"
    "RECNRQEVSAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEI"
    "ATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQ"
)
_AA = "ACDEFGHIKLMNPQRSTVWY"
_LIGANDS = (
    "Cc1ccc(NC(=O)c2ccc(CN3CC[NH+](C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1",
    "CN1CCN(CC1)Cc1ccc(cc1)C(=O)Nc1ccc(C)cc1",
    "CCOC(=O)c1ccc(Nc2ncccn2)cc1",
    "CC(=O)Nc1ccc(O)cc1",
    "COc1ccc2nc(NC(=O)c3ccccc3)sc2c1",
    "CCN(CC)CCOc1ccc2ncnc(Nc3ccc(F)c(Cl)c3)c2c1",
    "c1ccc2[nH]c(C3CCNCC3)nc2c1",
    "CC(C)c1nc(Nc2ccc(F)cc2)ncc1C(=O)N",
    "COc1cc2ncnc(Nc3ccc(OCCCN4CCOCC4)cc3)c2cc1OC",
)


def _mutate(sequence: str, count: int, rng: random.Random) -> str:
    chars = list(sequence)
    protected = {79, 104, 129}
    choices = [index for index in range(len(chars)) if index not in protected]
    for position in rng.sample(choices, min(count, len(choices))):
        chars[position] = rng.choice(_AA.replace(chars[position], ""))
    return "".join(chars)


def _nearest_residues(pdb: str, center: tuple[float, float, float], count: int = 3) -> set[int]:
    distances = []
    for line in pdb.splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            coordinates = tuple(float(line[start : start + 8]) for start in (30, 38, 46))
            distance = sum((coordinates[axis] - center[axis]) ** 2 for axis in range(3))
            distances.append((distance, int(line[22:26])))
    return {residue for _, residue in sorted(distances)[:count]}


@register
class ConformationLigandFamily:
    family_id = "conformation-ligand-triage"
    config_model = ConformationLigandFamilySpec
    defaults = {  # noqa: RUF012
        Difficulty.EASY: dict(num_receptors=4, num_ligands=5, receptor_length=150),
        Difficulty.MEDIUM: dict(num_receptors=5, num_ligands=6, receptor_length=220),
        Difficulty.HARD: dict(num_receptors=7, num_ligands=8, receptor_length=274),
    }
    tools = (
        "esmfold-prediction",
        "usalign-alignment",
        "pymol-rmsd-alignment",
        "dssp-secondary-structure",
        "vina-docking",
    )
    supported_sources = ("closed-world",)

    def generate(self, spec: ScenarioSpec, context: GenerationContext) -> FamilyResult:
        runtime = context.runtime
        config = spec.family
        if not isinstance(config, ConformationLigandFamilySpec):
            raise TypeError("invalid conformation ligand family spec")
        rng = random.Random(spec.seed)
        reference = _RECEPTOR[: config.receptor_length]
        mutation_counts = [
            2 + round(index * config.receptor_length * 0.18 / max(1, config.num_receptors - 1))
            for index in range(config.num_receptors)
        ]
        receptors = [_mutate(reference, count, rng) for count in mutation_counts]
        raw_ids = [f"receptor_state_{index:03d}" for index in range(1, config.num_receptors + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        sample_ids = [mapping[raw] for raw in raw_ids]
        predicted = runtime.run_tool(
            "esmfold-prediction",
            {"complexes": [reference, *receptors]},
            {"num_recycles": 6, "max_batch_residues": 1400},
        )["structures"]
        structures = [item["structure"] for item in predicted]
        secondary = runtime.run_tool("dssp-secondary-structure", {"inputs": structures}, {})["results"]
        reference_ss = secondary[0]
        comparisons: dict[str, dict[str, float]] = {}
        structural_scores: dict[str, float] = {}
        for position, sample in enumerate(sample_ids, start=1):
            usalign = runtime.run_tool(
                "usalign-alignment",
                {"query_structure": structures[position], "reference_structure": structures[0]},
                {},
            )
            pymol = runtime.run_tool(
                "pymol-rmsd-alignment",
                {"mobile_structure": structures[position], "target_structure": structures[0]},
                {"method": "align", "target_selection": "target and name CA", "mobile_selection": "mobile and name CA"},
            )
            tm_score = float(usalign["metrics"]["tm_score_structure_2"])
            rmsd = float(pymol["metrics"]["rmsd"])
            ss_distance = sum(
                abs(float(secondary[position][field]) - float(reference_ss[field]))
                for field in ("helix_pct", "sheet_pct", "loop_pct")
            ) / 200
            confidence = float(predicted[position]["metrics"]["avg_plddt"])
            comparisons[sample] = {
                "tm_score": tm_score,
                "rmsd": rmsd,
                "ss_distance": ss_distance,
                "confidence": confidence,
            }
            structural_scores[sample] = 0.55 * tm_score + 0.2 * confidence + 0.15 / (1 + rmsd) + 0.1 * (1 - ss_distance)
        receptor_sample = max(sample_ids, key=lambda sample: (structural_scores[sample], sample))
        from proto_tools.tools.molecular_docking.vina.vina_docking import example_input

        binding_scaffold = example_input().receptor.structure_pdb
        center = (15.190, 53.903, 16.917)
        site_residues = _nearest_residues(binding_scaffold, center)
        ligands = list(_LIGANDS[: config.num_ligands])
        docking = runtime.run_tool(
            "vina-docking",
            {
                "receptor": binding_scaffold,
                "ligands": ligands,
                "search_box": {"mode": "coordinates", "center": center, "size": (24.0, 24.0, 24.0)},
            },
            {"cpu": 4, "exhaustiveness": 6, "num_poses": 4, "energy_range": 4.0, "seed": spec.seed + 31},
        )
        ligand_scores: dict[str, float] = {}
        for index, result in enumerate(docking["results"], start=1):
            poses = result["poses"]
            best_affinity = min(float(pose["metrics"]["affinity"]) for pose in poses)
            mean_spread = sum(float(pose["metrics"]["rmsd_lower_bound"]) for pose in poses) / len(poses)
            ligand_scores[f"Compound_{index:02d}"] = -best_affinity - 0.03 * mean_spread
        compound = max(ligand_scores, key=lambda name: (ligand_scores[name], name))

        public_files = {
            "data/reference_state.pdb": structures[0],
            "data/binding_scaffold.pdb": binding_scaffold,
            "data/receptor_sequences.fasta": fasta(sorted(zip(sample_ids, receptors, strict=True))),
            "data/site_residues.tsv": "chain\tresidue\n"
            + "".join(f"A\t{residue}\n" for residue in sorted(site_residues)),
            "data/compounds.tsv": "compound\tsmiles\n" + "".join(
                f"Compound_{index:02d}\t{smiles}\n" for index, smiles in enumerate(ligands, start=1)
            ),
        }
        public_files.update(
            {
                f"data/receptor_candidates/{sample}.pdb": structures[position]
                for position, sample in enumerate(sample_ids, start=1)
            }
        )
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "raw_receptor_sequences": dict(zip(raw_ids, receptors, strict=True)),
                    "structural_comparisons": comparisons,
                    "structural_scores": structural_scores,
                    "selected_receptor": receptor_sample,
                    "site_center": center,
                    "ligand_scores": ligand_scores,
                    "selected_compound": compound,
                },
                anonymization_map=mapping,
                evidence={"predictions": predicted, "secondary_structure": secondary, "docking": docking},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    ExactAssertion(field="receptor", expected=receptor_sample),
                    ExactAssertion(field="compound", expected=compound),
                ],
                rubric_text=f"Credit requires receptor {receptor_sample} and ligand {compound}.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Select a fold-preserving receptor state and its best-supported ligand",
                public_files=sorted(public_files),
                answer_format="receptor: Sample_...\ncompound: Compound_...",
                default_question=(
                    "The structures under `data/receptor_candidates/` are anonymous sequence variants of the "
                    "state represented by `data/reference_state.pdb`; their sequences are in "
                    "`data/receptor_sequences.fasta`. Select the variant that best preserves the global fold, "
                    "backbone geometry, secondary-structure balance, and model confidence. Then evaluate the "
                    "closed ligand panel in `data/compounds.tsv` against `data/binding_scaffold.pdb` at the "
                    "residue-defined site in `data/site_residues.tsv` and identify the compound with the strongest "
                    "pose support. Report the receptor and compound only after reconciling both the conformational "
                    "and binding evidence."
                ),
            ),
        )


CONFORMATION_LIGAND_FAMILY = ConformationLigandFamily()
