# Attribute a complete mobile element to its host and recover its boundaries

The anonymous sequences in `data/host_genomes.fasta` contain partial insertions, reversed decoys, rearranged boundary fragments, and one complete mobile element. Use the three probes in `data/boundary_probes.fasta` together with the expected cargo family in `data/cargo_marker.fasta` to identify the true host, the 1-based inclusive element interval, and its orientation. The accepted call must reconcile broad nucleotide homology, exact local boundary order, strand, element completeness, and an intact cargo coding region.

## Response format

host: Sample_...
element_interval: start-end
orientation: + or -
