from importlib import import_module

_MODULES = (
    "dna_motif",
    "rna_structure",
    "protein_structure",
    "protein_bridge",
    "crispr_linkage",
    "recombination",
    "utr_regulatory_assay",
    "metagenomic_enzyme",
)

for _module in _MODULES:
    import_module(f"bio_mystery_synth.task_families.{_module}")
