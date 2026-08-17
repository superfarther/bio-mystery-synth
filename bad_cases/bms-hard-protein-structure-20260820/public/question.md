# Rank protein candidates by structural similarity

Align each file under `data/candidates/` to `data/reference.pdb` with TM-align. Use the TM-score normalized by the reference length and report the complete descending ranking.

## Response format

A single descending ranking: Sample_A > Sample_B > ...
