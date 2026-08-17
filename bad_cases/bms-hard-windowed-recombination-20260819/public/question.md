# Detect mosaic isolates by windowed phylogenetic assignment

Align all records in `data/isolates.fasta` with MAFFT. Remove columns containing a gap in either reference, split the remaining alignment into consecutive 250-nt windows, and assign each sample window to the reference with lower Hamming distance; ties remain unassigned. Report samples with exactly one A-to-B switch and the 1-based first coordinate of the first B-assigned window.

## Response format

One line per recombinant: Sample_ID:first_coordinate_of_B_window.
