# Resolve the expressed intact member of a divergent synthetic cassette family

The anonymous DNA cassettes in `data/cassettes.fasta` contain unrelated background, partial relatives, strand decoys, and several divergent members of the family represented by `data/family_marker.fasta`. Identify the single cassette that combines a complete coding region with the strongest plausible forward bacterial promoter immediately upstream. Report the 1-based transcription start and the 1-based inclusive coding interval, including the terminal stop codon. Sequence similarity, gene boundaries, strand, and promoter strength must agree; no one signal is decisive by itself.

## Response format

sample: Sample_...
tss: integer
orf_interval: start-end
