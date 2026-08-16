# Rescue a remote homolog by reconciling profile and fold evidence

Use the closed candidate collection in `data/candidates.fasta`, the seed alignment material in `data/profile_seeds.fasta`, its supplied family profile in `data/family_profile.hmm`, and the reference structure in `data/reference_fold.pdb`. First identify the strongest profile-supported remote relatives, retaining 7 candidates. Among that set, identify the single candidate whose predicted fold most convincingly preserves the reference topology and secondary-structure composition while remaining well resolved. Report the 7-member shortlist and the final winner. The final call must integrate sequence-profile, global fold, structural clustering, confidence, and secondary-structure evidence.

## Response format

shortlist: Sample_..., ...
winner: Sample_...
