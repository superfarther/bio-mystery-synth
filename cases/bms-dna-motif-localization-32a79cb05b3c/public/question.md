# Locate the synthetic DNA motif

Scan `data/sequences.fasta` with the PWM in `data/motif.meme`. Identify every sequence carrying the synthetic motif and report its 1-based inclusive interval and strand. Report only motif hits.

## Response format

One tuple per line: Sample_ID:start-end:strand, using 1-based inclusive coordinates.
