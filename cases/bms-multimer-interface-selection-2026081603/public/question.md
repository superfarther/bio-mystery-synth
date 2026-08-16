# Prioritize sequence-diverse binders by coherent multimer interface evidence

`data/binders.fasta` contains a diverse synthetic binder panel for the protein in `data/target.fasta`. Rank the three most credible binders. A defensible ranking must account for sequence redundancy, the geometry of predicted two-chain assemblies, uncertainty both within and across the interface, local contact density, and overall model confidence. Treat apparent contacts unsupported by cross-chain confidence as decoys, and do not let a single headline score override contradictory interface evidence.

## Response format

top_three: Sample_... > Sample_... > Sample_...
