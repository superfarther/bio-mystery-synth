# Find stable structural mimics concealed by sequence divergence

The sequence and coordinate cohort under `data/` contains remote variants, rearranged decoys, and true structural mimics of the anchor. Identify the six candidates with the strongest positive disagreement between weak sequence similarity and retained three-dimensional topology, while penalizing disruption of the cohort's conserved structural core. Rank those six by the coherence of physical energy, solvent exposure, model confidence, and secondary-structure composition. Report both the unordered six-member shortlist and its final stability ranking.

## Response format

shortlist: Sample_..., Sample_..., Sample_..., Sample_..., Sample_..., Sample_...
ranking: Sample_... > Sample_... > Sample_... > Sample_... > Sample_... > Sample_...
