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
    "promoter_cassette",
    "profile_fold",
    "multimer_interface",
    "conformation_ligand",
    "mobile_element",
    "protein_repair",
    "structural_discordance",
    "metagenomic_stability",
)

for _module in _MODULES:
    import_module(f"bio_mystery_synth.task_families.{_module}")
