"""Closed-world proto-tools catalog."""

from __future__ import annotations

from itertools import chain
from typing import Any

FAMILY_TOOLS = {
    "dna-motif-localization": ["random-nucleotide-sample", "meme-fimo-scan"],
    "rna-structure-ranking": ["random-nucleotide-sample", "viennarna-prediction"],
    "protein-structure-nearest": [
        "random-protein-sample",
        "esmfold-prediction",
        "tmalign-alignment",
    ],
    "protein-bridge-triage": [
        "random-protein-sample",
        "esmfold-prediction",
        "structure-metrics",
        "tmalign-alignment",
        "mafft-align",
    ],
    "crispr-spacer-linkage": ["minced-crispr"],
    "windowed-recombination": ["mafft-align"],
    "utr-regulatory-assay": [
        "orfipy-prediction",
        "miranda-scan",
        "viennarna-prediction",
        "primer3-thermodynamics",
    ],
    "metagenomic-enzyme-forensics": [
        "prodigal-prediction",
        "pyhmmer-phmmer",
        "esmfold-prediction",
        "structure-metrics",
        "tmalign-alignment",
    ],
}

TOOL_GROUPS = {
    "promoter-context": ["promoter-calculator"],
    "profile-and-local-homology": [
        "pyhmmer-hmmscan",
        "pyhmmer-hmmsearch",
        "pyhmmer-jackhmmer",
        "pyhmmer-nhmmer",
        "blast-create-db",
        "blast-search",
        "mmseqs2-clustering",
        "mmseqs2-search-genomes",
    ],
    "structure-comparison": [
        "foldseek-cluster",
        "foldseek-multimercluster",
        "pymol-rmsd-alignment",
        "usalign-alignment",
        "dssp-secondary-structure",
    ],
    "molecular-interaction": [
        "vina-docking",
        "ipsae-scoring",
        "pdockq2",
    ],
}

CLOSED_WORLD_CONFIG = {
    "blast-search": {"search_mode": "local"},
}

CLOSED_WORLD_REQUIRED_CONFIG = {
    "blast-search": ("local_db",),
}

CURATED_TOOLS = frozenset(chain.from_iterable([*FAMILY_TOOLS.values(), *TOOL_GROUPS.values()]))


def apply_closed_world_config(tool: str, config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(config)
    for key, required in CLOSED_WORLD_CONFIG.get(tool, {}).items():
        actual = merged.setdefault(key, required)
        if actual != required:
            raise ValueError(f"closed-world generation requires {tool}.{key}={required!r}")
    missing = [key for key in CLOSED_WORLD_REQUIRED_CONFIG.get(tool, ()) if not merged.get(key)]
    if missing:
        raise ValueError(f"closed-world generation requires {tool} config: {', '.join(missing)}")
    return merged
