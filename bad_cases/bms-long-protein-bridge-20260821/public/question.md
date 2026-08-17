# Find and rank proteins that structurally bridge two anchor folds

Use only `data/proteins.fasta` and the following pipeline. Predict all structures with `esmfold-prediction` using `num_recycles=4` and `max_batch_residues=1200`. Run `structure-metrics` on those predictions. For every candidate, run TM-align twice with the candidate as query and each anchor as reference; use `tm_score_chain_2`. Let R be its gyration radius and R0 the mean anchor radius. Compute T = 0.85*min(TM_A, TM_B) + 0.15/(1+abs(R-R0)). Retain the four highest-T candidates, breaking exact ties by sample ID. Run MAFFT on the two anchors and these four candidates with `align_method=auto`, `max_iterations=0`, and one thread. For each finalist, calculate ungapped pairwise identity to each anchor (exclude columns containing a gap in either member), and let I be the smaller identity. Compute F = 0.9*T + 0.1*I and rank all four by descending F, again breaking exact ties by sample ID. Report both the unordered shortlist and complete final ranking.

## Response format

shortlist: Sample_..., ...
ranking: Sample_... > Sample_... > ...
