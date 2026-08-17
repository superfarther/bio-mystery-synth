### bms-profile-fold-rescue-2026081602

英文问题：

```text
# Rescue a remote homolog by reconciling profile and fold evidence

Use the closed candidate collection in `data/candidates.fasta`, the seed alignment material in `data/profile_seeds.fasta`, its supplied family profile in `data/family_profile.hmm`, and the reference structure in `data/reference_fold.pdb`. First identify the strongest profile-supported remote relatives, retaining 7 candidates. Among that set, identify the single candidate whose predicted fold most convincingly preserves the reference topology and secondary-structure composition while remaining well resolved. Report the 7-member shortlist and the final winner. The final call must integrate sequence-profile, global fold, structural clustering, confidence, and secondary-structure evidence.

## Response format

shortlist: Sample_..., ...
winner: Sample_...
```

中文问题：

```text
# 综合序列谱与折叠证据挽救远缘同源物

请使用 `data/candidates.fasta` 中的封闭候选集合、`data/profile_seeds.fasta` 中的种子比对材料、随附的家族序列谱 `data/family_profile.hmm`，以及 `data/reference_fold.pdb` 中的参考结构。首先识别得到序列谱最强支持的远缘亲属，并保留 7 个候选。然后从中找出唯一一个候选：其预测折叠在结构清晰、置信度良好的同时，最有力地保持了参考拓扑和二级结构组成。请报告由 7 个成员组成的候选短名单和最终胜出者。最终判断必须综合序列谱、整体折叠、结构聚类、置信度及二级结构证据。

## 输出格式

shortlist: Sample_..., ...
winner: Sample_...
```

答案：

```json
[
  {
    "expected": [
      "Sample_006",
      "Sample_002",
      "Sample_005",
      "Sample_010",
      "Sample_012",
      "Sample_011",
      "Sample_009"
    ],
    "field": "shortlist",
    "kind": "unordered_set"
  },
  {
    "case_sensitive": false,
    "expected": "Sample_002",
    "field": "winner",
    "kind": "exact"
  }
]
```

Rubric：Credit requires shortlist Sample_006, Sample_002, Sample_005, Sample_010, Sample_012, Sample_011, Sample_009 and winner Sample_002.

任务类型：`profile-fold-rescue`（序列谱—折叠联合挽救）

预期中，Agent 解决本问题需要调用的工具数：12
