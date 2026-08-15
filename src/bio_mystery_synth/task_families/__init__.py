"""Built-in task families."""

from bio_mystery_synth.task_families.base import FAMILIES, get_family
from bio_mystery_synth.task_families.dna_motif import DNA_MOTIF_FAMILY
from bio_mystery_synth.task_families.protein_structure import PROTEIN_STRUCTURE_FAMILY
from bio_mystery_synth.task_families.rna_structure import RNA_STRUCTURE_FAMILY

__all__ = [
    "DNA_MOTIF_FAMILY",
    "FAMILIES",
    "PROTEIN_STRUCTURE_FAMILY",
    "RNA_STRUCTURE_FAMILY",
    "get_family",
]
