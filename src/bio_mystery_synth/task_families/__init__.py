"""Built-in task families."""

from bio_mystery_synth.task_families.base import FAMILIES, get_family
from bio_mystery_synth.task_families.crispr_linkage import CRISPR_LINKAGE_FAMILY
from bio_mystery_synth.task_families.dna_motif import DNA_MOTIF_FAMILY
from bio_mystery_synth.task_families.protein_bridge import PROTEIN_BRIDGE_FAMILY
from bio_mystery_synth.task_families.protein_structure import PROTEIN_STRUCTURE_FAMILY
from bio_mystery_synth.task_families.recombination import RECOMBINATION_FAMILY
from bio_mystery_synth.task_families.rna_structure import RNA_STRUCTURE_FAMILY

__all__ = [
    "CRISPR_LINKAGE_FAMILY",
    "DNA_MOTIF_FAMILY",
    "FAMILIES",
    "PROTEIN_BRIDGE_FAMILY",
    "PROTEIN_STRUCTURE_FAMILY",
    "RECOMBINATION_FAMILY",
    "RNA_STRUCTURE_FAMILY",
    "get_family",
]
