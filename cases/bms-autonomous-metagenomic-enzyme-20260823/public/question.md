# Find the intact enzyme-family member hidden in anonymous metagenomic contigs

`data/contigs.fasta` contains synthetic metagenomic fragments with truncated genes, compositionally biased mimics, and several divergent relatives of the protein in `data/family_marker.fasta`. Identify the single most credible intact family member and its 1-based inclusive coding interval, including the terminal stop codon when present. A defensible call must reconcile prokaryotic gene boundaries, statistically meaningful full-length homology, low compositional bias, and a compact, high-confidence predicted fold; no one signal is sufficient on its own.

## Response format

sample: Sample_...
orf_interval: start-end
