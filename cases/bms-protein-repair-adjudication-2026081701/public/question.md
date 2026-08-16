# Prioritize repaired proteins across sequence, sensitivity, fold, and stability evidence

The anonymous repair panel, its common reference, and corresponding coordinate models are under `data/`. Rank the five repairs most likely to restore a robust member of the reference family. Reconcile whole-sequence plausibility, representation-space proximity, sensitivity of the reference sequence landscape, preservation of the global fold and secondary-structure balance, whole-structure physical energy, and burial of sensitive sites. A candidate that excels on only one evidence class should not outrank a consistently supported repair.

## Response format

top_five: Sample_... > Sample_... > Sample_... > Sample_... > Sample_...
