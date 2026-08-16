"""Long-horizon UTR regulation and assay-selection family."""

from __future__ import annotations

import random
from pathlib import Path

from bio_mystery_synth.models import (
    AnswerSpec,
    ExactAssertion,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    ScenarioSpec,
    UTRRegulatoryAssayFamilySpec,
)
from bio_mystery_synth.runtime import Runtime
from bio_mystery_synth.task_families.base import register
from bio_mystery_synth.utils import anonymize, fasta, reverse_complement

CODONS = {
    "A": "GCT",
    "C": "TGT",
    "D": "GAT",
    "E": "GAA",
    "F": "TTT",
    "G": "GGT",
    "H": "CAT",
    "I": "ATT",
    "K": "AAA",
    "L": "CTG",
    "M": "ATG",
    "N": "AAT",
    "P": "CCT",
    "Q": "CAA",
    "R": "CGT",
    "S": "TCT",
    "T": "ACT",
    "V": "GTT",
    "W": "TGG",
    "Y": "TAT",
}


def _coding_sequence(protein: str) -> str:
    return "ATG" + "".join(CODONS[aa] for aa in protein[1:]) + "TAA"


def _site_accessibility(structure: str, start: int, end: int) -> float:
    region = structure[start:end]
    return region.count(".") / len(region)


def _primer_penalty(forward: dict[str, object], reverse: dict[str, object]) -> float:
    tm_f, tm_r = float(forward["tm"]), float(reverse["tm"])
    penalty = abs(tm_f - 60) + abs(tm_r - 60) + 2 * abs(tm_f - tm_r)
    for result in (forward, reverse):
        penalty += max(0.0, -float(result["hairpin_dg"]) - 3)
        penalty += max(0.0, -float(result["homodimer_dg"]) - 5)
        hetero = result.get("heterodimer_dg")
        if hetero is not None:
            penalty += max(0.0, -float(hetero) - 7)
    return penalty


@register
class UTRRegulatoryAssayFamily:
    family_id = "utr-regulatory-assay"

    def generate(self, spec: ScenarioSpec, runtime: Runtime, workspace: Path) -> FamilyResult:
        del workspace
        config = spec.family
        if not isinstance(config, UTRRegulatoryAssayFamilySpec):
            raise TypeError("invalid UTR regulatory assay family spec")
        rng = random.Random(spec.seed)
        proteins = runtime.generate_sequences("protein", config.num_transcripts, config.coding_aa_length, spec.seed)
        coding = [_coding_sequence("M" + protein[1:]) for protein in proteins]
        utrs = runtime.generate_sequences("dna", config.num_transcripts, config.utr_length, spec.seed + 1, 0.45)
        mirnas = [
            sequence.replace("T", "U")
            for sequence in runtime.generate_sequences(
                "rna", config.num_mirnas, config.mirna_length, spec.seed + 2, 0.45
            )
        ]
        mirna_ids = [f"miR_SYN_{index:02d}" for index in range(1, config.num_mirnas + 1)]
        target = reverse_complement(mirnas[0].replace("U", "T"))
        site_start = config.utr_length // 2 - len(target) // 2
        roles = ["accessible", "structured", "early_stop", "coding_site", *(["neutral"] * config.num_transcripts)]
        roles = roles[: config.num_transcripts]
        for index, role in enumerate(roles):
            if role in {"accessible", "early_stop"}:
                insert = "A" * 24 + target + "A" * 24
                start = site_start - 24
                utrs[index] = utrs[index][:start] + insert + utrs[index][start + len(insert) :]
            elif role == "structured":
                insert = target + "AAAAAA" + reverse_complement(target)
                utrs[index] = utrs[index][:site_start] + insert + utrs[index][site_start + len(insert) :]
            elif role == "coding_site":
                position = len(coding[index]) - len(target) - 18
                coding[index] = coding[index][:position] + target + coding[index][position + len(target) :]
        stop_position = len(coding[2]) // 2
        stop_position -= stop_position % 3
        coding[2] = coding[2][:stop_position] + "TAA" + coding[2][stop_position + 3 :]
        transcripts = [cds + utr for cds, utr in zip(coding, utrs, strict=True)]

        raw_ids = [f"transcript_{index:03d}" for index in range(1, config.num_transcripts + 1)]
        mapping = anonymize(raw_ids, spec.anonymization, rng)
        runtime.run_tool(
            "orfipy-prediction",
            {"sequences": transcripts},
            {"start_codons": ["ATG"], "strand": "f", "min_len": config.coding_aa_length * 2},
        )
        complete = [index for index, role in enumerate(roles) if role != "early_stop"]
        utr_scan = runtime.run_tool(
            "miranda-scan",
            {"target_sequences": [utrs[index] for index in complete]},
            {
                "mirna_queries": mirnas,
                "mirna_ids": mirna_ids,
                "score_threshold": 80,
                "energy_threshold": -10,
                "strict": True,
            },
        )
        sites: list[tuple[int, dict[str, object]]] = []
        for result_index, result in enumerate(utr_scan["results"]):
            for site in result["target_sites"]:
                if float(site["identity"]) >= 90:
                    sites.append((complete[result_index], site))
        if not sites:
            raise RuntimeError("no high-confidence miRNA site was recovered")
        best_site_by_transcript: dict[int, dict[str, object]] = {}
        for index, site in sites:
            current = best_site_by_transcript.get(index)
            if current is None or (float(site["score"]), -float(site["energy"])) > (
                float(current["score"]),
                -float(current["energy"]),
            ):
                best_site_by_transcript[index] = site

        fold_indexes = sorted(best_site_by_transcript)
        windows: list[str] = []
        offsets: list[int] = []
        for index in fold_indexes:
            site = best_site_by_transcript[index]
            center = (int(site["target_start"]) - 1 + int(site["target_end"])) // 2
            start = max(0, min(config.utr_length - config.fold_window, center - config.fold_window // 2))
            windows.append(utrs[index][start : start + config.fold_window].replace("T", "U"))
            offsets.append(start)
        folded = runtime.run_tool("viennarna-prediction", {"sequences": windows}, {})["results"]
        accessibility: dict[int, float] = {}
        for index, offset, result in zip(fold_indexes, offsets, folded, strict=True):
            site = best_site_by_transcript[index]
            start = int(site["target_start"]) - 1 - offset
            end = int(site["target_end"]) - offset
            accessibility[index] = _site_accessibility(result["structure"], start, end)
        winner = max(accessibility, key=lambda index: (accessibility[index], -index))
        winner_site = best_site_by_transcript[winner]

        primer_rows: list[tuple[str, int, str, str]] = []
        for index, transcript in enumerate(transcripts):
            for pair_index in range(config.primer_pairs_per_transcript):
                length = 18 + pair_index
                left = 12 + pair_index * 7
                right = len(transcript) - 35 - pair_index * 9
                forward = transcript[left : left + length]
                reverse = reverse_complement(transcript[right - length : right])
                primer_rows.append((f"Pair_{index + 1:02d}_{pair_index + 1:02d}", index, forward, reverse))
        oligos = [
            item
            for _, _, forward, reverse in primer_rows
            for item in ({"sequence": forward, "partner": reverse}, {"sequence": reverse, "partner": forward})
        ]
        primer_results = runtime.run_tool("primer3-thermodynamics", {"oligos": oligos}, {})["results"]
        primer_scores = {
            pair_id: _primer_penalty(primer_results[2 * row], primer_results[2 * row + 1])
            for row, (pair_id, index, _, _) in enumerate(primer_rows)
            if index == winner
        }
        best_pair = min(primer_scores, key=lambda pair_id: (primer_scores[pair_id], pair_id))
        winner_sample = mapping[raw_ids[winner]]

        primer_table = "pair_id\tsample\tforward\treverse\n" + "".join(
            f"{pair_id}\t{mapping[raw_ids[index]]}\t{forward}\t{reverse}\n"
            for pair_id, index, forward, reverse in primer_rows
        )
        public_files = {
            "data/transcripts.fasta": fasta(
                sorted((mapping[raw], sequence) for raw, sequence in zip(raw_ids, transcripts, strict=True))
            ),
            "data/mirnas.fasta": fasta(list(zip(mirna_ids, mirnas, strict=True))),
            "data/primer_pairs.tsv": primer_table,
        }
        answer_mirna = str(winner_site["mirna_id"])
        return FamilyResult(
            public_files=public_files,
            ground_truth=GroundTruth(
                oracle_type=OracleType.MODEL_DEFINED,
                facts={
                    "raw_transcripts": dict(zip(raw_ids, transcripts, strict=True)),
                    "roles": dict(zip(raw_ids, roles, strict=True)),
                    "mirnas": dict(zip(mirna_ids, mirnas, strict=True)),
                    "complete_orf_indexes": complete,
                    "miRNA_sites": best_site_by_transcript,
                    "accessibility": accessibility,
                    "winner": winner_sample,
                    "winner_mirna": answer_mirna,
                    "primer_scores": primer_scores,
                    "best_primer_pair": best_pair,
                },
                anonymization_map=mapping,
                evidence={"miranda": utr_scan, "folds": folded, "primer_thermodynamics": primer_results},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.MODEL_DEFINED,
                assertions=[
                    ExactAssertion(field="sample", expected=winner_sample),
                    ExactAssertion(field="mirna", expected=answer_mirna),
                    ExactAssertion(field="primer_pair", expected=best_pair),
                ],
                rubric_text=f"Credit requires {winner_sample}, {answer_mirna}, and {best_pair}.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Resolve a hidden UTR regulatory event and its diagnostic assay",
                public_files=sorted(public_files),
                answer_format="sample: Sample_...\nmiRNA: miR_SYN_...\nprimer_pair: Pair_...",
                default_question=(
                    "The anonymous records in `data/transcripts.fasta` are competing synthetic isoforms. Exactly one "
                    "combines an intact long coding region with a near-perfect site for a sequence in "
                    "`data/mirnas.fasta` that lies in the resulting 3' UTR and is the most locally exposed in the "
                    "minimum-free-energy fold. Identify that isoform and miRNA. Then choose, from "
                    "`data/primer_pairs.tsv`, the matching diagnostic pair with closely balanced melting behavior "
                    "near 60 °C and the weakest combined hairpin, self-dimer, and cross-dimer liabilities. Reconcile "
                    "all evidence rather than treating a sequence match alone as sufficient."
                ),
            ),
        )


UTR_REGULATORY_ASSAY_FAMILY = UTRRegulatoryAssayFamily()
