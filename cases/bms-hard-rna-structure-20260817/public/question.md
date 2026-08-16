# Rank RNA candidates by secondary-structure similarity

Fold every sequence in `data/sequences.fasta` with ViennaRNA at 37 °C. Compare each candidate with `Reference` using Jaccard similarity of 0-based base-pair sets and report the complete descending ranking.

## Response format

A single descending ranking: Sample_A > Sample_B > ...
