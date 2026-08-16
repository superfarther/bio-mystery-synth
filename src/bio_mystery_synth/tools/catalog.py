from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    groups: tuple[str, ...] = ()


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
    "molecular-interaction": ["vina-docking", "ipsae-scoring", "pdockq2"],
}

_BUILTIN_TOOLS = {
    "random-nucleotide-sample",
    "meme-fimo-scan",
    "viennarna-prediction",
    "random-protein-sample",
    "esmfold-prediction",
    "tmalign-alignment",
    "structure-metrics",
    "mafft-align",
    "minced-crispr",
    "orfipy-prediction",
    "miranda-scan",
    "primer3-thermodynamics",
    "prodigal-prediction",
    "pyhmmer-phmmer",
}

CURATED_TOOLS = frozenset(_BUILTIN_TOOLS | {tool for tools in TOOL_GROUPS.values() for tool in tools})


def tool_descriptors() -> dict[str, ToolDescriptor]:
    memberships = {
        tool: tuple(group for group, tools in TOOL_GROUPS.items() if tool in tools) for tool in CURATED_TOOLS
    }
    return {tool: ToolDescriptor(tool, memberships[tool]) for tool in sorted(CURATED_TOOLS)}
