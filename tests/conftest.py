from __future__ import annotations

import random
import re
import time
from typing import Any

from bio_mystery_synth.models import Backend, ToolCallRecord


class FakeRuntime:
    def __init__(self, seed: int = 1) -> None:
        self.rng = random.Random(seed)
        self.calls: list[ToolCallRecord] = []

    def _record(self, tool: str, config: dict[str, Any] | None = None) -> None:
        self.calls.append(
            ToolCallRecord(
                tool=tool,
                backend=Backend.LOCAL,
                device="cpu",
                config=config or {},
                duration_seconds=0.0,
                ok=True,
            )
        )

    def generate_sequences(
        self,
        sequence_type: str,
        count: int,
        length: int,
        seed: int,
        gc_fraction: float | None = None,
    ) -> list[str]:
        del seed, gc_fraction
        alphabet = {"dna": "ACGT", "rna": "ACGU", "protein": "ACDEFGHIKLMNPQRSTVWY"}[sequence_type]
        self._record(f"proto-language:random-{sequence_type}")
        return ["".join(self.rng.choice(alphabet) for _ in range(length)) for _ in range(count)]

    def run_tool(self, tool: str, inputs: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.monotonic()
        if tool == "random-nucleotide-sample":
            alphabet = "ACGU"
            results = []
            for candidate_index, sequence in enumerate(inputs["sequences"]):
                chars = [
                    alphabet[(position + candidate_index) % len(alphabet)] if char == "_" else char
                    for position, char in enumerate(sequence)
                ]
                results.append({"sequence": "".join(chars)})
            output = {"results": results}
        elif tool == "random-protein-sample":
            alphabet = "ACDEFGHIKLMNPQRSTVWY"
            results = []
            for candidate_index, sequence in enumerate(inputs["sequences"]):
                chars = [
                    alphabet[(position + candidate_index) % len(alphabet)] if char == "_" else char
                    for position, char in enumerate(sequence)
                ]
                results.append({"sequence": "".join(chars)})
            output = {"results": results}
        elif tool == "meme-fimo-scan":
            output = {"results": [{"matches": []} for _ in inputs["sequences"]]}
        elif tool == "viennarna-prediction":
            results = []
            for index, sequence in enumerate(inputs["sequences"]):
                pairs = max(1, min(8, len(sequence) // 3) - index)
                structure = "(" * pairs + "." * (len(sequence) - 2 * pairs) + ")" * pairs
                results.append({"sequence": sequence, "structure": structure, "mfe": -float(pairs)})
            output = {"results": results}
        elif tool == "esmfold-prediction":
            output = {
                "structures": [
                    {
                        "structure": f"MODEL {index}\nEND\n",
                        "structure_format": "pdb",
                        "metrics": {"avg_plddt": 0.9 - index / 100, "ptm": 0.7, "avg_pae": 4.0},
                    }
                    for index, _ in enumerate(inputs["complexes"])
                ]
            }
        elif tool == "tmalign-alignment":
            match = re.search(r"MODEL (\d+)", inputs["query_structure"])
            index = int(match.group(1)) if match else 9
            output = {"metrics": {"tm_score_chain_1": 1 - index / 10, "tm_score_chain_2": 1 - index / 10}}
        elif tool == "structure-metrics":
            output = {
                "metrics": [
                    {
                        "longest_alpha_helix": 10,
                        "gyration_radius": 10.0 + index,
                        "helix_pct": 40.0,
                        "sheet_pct": 20.0,
                        "loop_pct": 40.0,
                    }
                    for index, _ in enumerate(inputs["structures"])
                ]
            }
        elif tool == "minced-crispr":
            output = {
                "results": [
                    {"sequence_id": f"seq_{index}", "crispr_arrays": []} for index in range(len(inputs["sequences"]))
                ]
            }
        elif tool == "mafft-align":
            output = {
                "metadata": {"num_sequences": len(inputs["sequences"])},
                "msa": {"aligned_sequences": inputs["sequences"], "sequence_ids": inputs.get("sequence_ids")},
            }
        elif tool == "orfipy-prediction":
            output = {"results": [{"orfs": []} for _ in inputs["sequences"]]}
        elif tool == "prodigal-prediction":
            codons = {
                "GCT": "A",
                "TGT": "C",
                "GAT": "D",
                "GAA": "E",
                "TTT": "F",
                "GGT": "G",
                "CAT": "H",
                "ATT": "I",
                "AAA": "K",
                "CTG": "L",
                "ATG": "M",
                "AAT": "N",
                "CCT": "P",
                "CAA": "Q",
                "CGT": "R",
                "TCT": "S",
                "ACT": "T",
                "GTT": "V",
                "TGG": "W",
                "TAT": "Y",
            }
            results = []
            prefix = "AGGAGGAAAA"
            for sequence in inputs["input_sequences"]:
                begin = sequence.find(prefix)
                orfs = []
                if begin >= 0:
                    start = begin + len(prefix)
                    stop = next(
                        position
                        for position in range(start + 3, len(sequence) - 2, 3)
                        if sequence[position : position + 3] == "TAA"
                    )
                    protein = "".join(codons[sequence[position : position + 3]] for position in range(start, stop, 3))
                    orfs.append(
                        {
                            "parent_id": "seq_0",
                            "orf_id": "gene_1",
                            "strand": "+",
                            "frame": 1,
                            "amino_acid_sequence": protein,
                            "nucleotide_sequence": sequence[start : stop + 3],
                            "amino_acid_length": len(protein),
                            "nucleotide_length": stop + 3 - start,
                            "nucleotide_start": start + 1,
                            "nucleotide_end": stop + 3,
                            "metrics": {},
                        }
                    )
                results.append({"orfs": orfs})
            output = {"results": results}
        elif tool == "pyhmmer-phmmer":
            output = {"sequence_hits": [], "domain_hits": [], "metadata": {}}
        elif tool == "segmasker-score":
            output = {
                "results": [
                    {
                        "low_complexity_fraction": max(sequence.count(aa) for aa in set(sequence)) / len(sequence),
                        "low_complexity_count": max(sequence.count(aa) for aa in set(sequence)),
                        "sequence_length": len(sequence),
                    }
                    for sequence in inputs["sequences"]
                ]
            }
        elif tool == "miranda-scan":
            queries = config["mirna_queries"]
            ids = config["mirna_ids"]
            results = []
            for target_index, target in enumerate(inputs["target_sequences"]):
                sites = []
                for mirna_id, query in zip(ids, queries, strict=True):
                    dna = query.replace("U", "T")
                    complement = dna.translate(str.maketrans("ACGT", "TGCA"))[::-1]
                    start = target.find(complement)
                    if start >= 0:
                        sites.append(
                            {
                                "mirna_id": mirna_id,
                                "score": 160.0,
                                "energy": -30.0,
                                "target_start": start + 1,
                                "target_end": start + len(complement),
                                "mirna_start": 1,
                                "mirna_end": len(query),
                                "alignment_length": len(query),
                                "identity": 100.0,
                                "similarity": 100.0,
                            }
                        )
                results.append(
                    {
                        "target_id": f"target_{target_index}",
                        "target_sequence": target,
                        "target_sites": sites,
                    }
                )
            output = {"results": results}
        elif tool == "primer3-thermodynamics":
            results = []
            for index, oligo in enumerate(inputs["oligos"]):
                sequence = oligo["sequence"]
                gc = sum(base in "GC" for base in sequence) / len(sequence)
                tm = 2 * sum(base in "AT" for base in sequence) + 4 * sum(base in "GC" for base in sequence)
                results.append(
                    {
                        "oligo_id": f"oligo_{index}",
                        "length": len(sequence),
                        "tm": float(tm),
                        "hairpin_dg": 0.0,
                        "homodimer_dg": 0.0,
                        "heterodimer_dg": 0.0,
                        "gc_content": gc,
                        "gc_clamp": sequence[-1] in "GC",
                        "hairpin_structure_found": False,
                        "homodimer_structure_found": False,
                        "heterodimer_structure_found": False,
                    }
                )
            output = {"results": results}
        else:
            raise ValueError(tool)
        self.calls.append(
            ToolCallRecord(
                tool=tool,
                backend=Backend.LOCAL,
                device="cpu",
                config=config or {},
                duration_seconds=time.monotonic() - started,
                ok=True,
            )
        )
        return output
