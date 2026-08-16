# Recover and rank stable enzyme-family members from a large anonymous metagenome

Search the complete anonymous contig collection under `data/` for intact relatives of the supplied synthetic family marker. Exclude truncated, compositionally biased, and rearranged mimics. From the remaining full-length relatives, report the three best-supported sample and 1-based inclusive coding intervals in order. The ranking must reconcile gene-boundary and homology evidence with whole-sequence plausibility, family-space proximity, conserved fold and secondary structure, physical energy, solvent exposure, and coordinate confidence; isolated evidence is insufficient.

## Response format

top_three: Sample_...:start-end > Sample_...:start-end > Sample_...:start-end
