# Select a fold-preserving receptor state and its best-supported ligand

The structures under `data/receptor_candidates/` are anonymous sequence variants of the state represented by `data/reference_state.pdb`; their sequences are in `data/receptor_sequences.fasta`. Select the variant that best preserves the global fold, backbone geometry, secondary-structure balance, and model confidence. Then evaluate the closed ligand panel in `data/compounds.tsv` against `data/binding_scaffold.pdb` at the residue-defined site in `data/site_residues.tsv` and identify the compound with the strongest pose support. Report the receptor and compound only after reconciling both the conformational and binding evidence.

## Response format

receptor: Sample_...
compound: Compound_...
