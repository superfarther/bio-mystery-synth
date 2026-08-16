# Link CRISPR arrays to synthetic challenge phages

Run MinCED on `data/host_genomes.fasta` using exactly 10 repeats, repeat length 28, and spacer length 32. For every detected array, match each spacer exactly against either strand of `data/challenge_phages.fasta`. Retain arrays with at least 5 matching spacers and report the 1-based inclusive array interval plus every uniquely linked phage in lexical order.

## Response format

One line per retained array: Sample_ID:start-end:comma-separated_Phage_IDs.
