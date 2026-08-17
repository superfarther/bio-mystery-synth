### bms-structural-discordance-cohort-2026081702

英文问题：

```text
# Find stable structural mimics concealed by sequence divergence

The sequence and coordinate cohort under `data/` contains remote variants, rearranged decoys, and true structural mimics of the anchor. Identify the six candidates with the strongest positive disagreement between weak sequence similarity and retained three-dimensional topology, while penalizing disruption of the cohort's conserved structural core. Rank those six by the coherence of physical energy, solvent exposure, model confidence, and secondary-structure composition. Report both the unordered six-member shortlist and its final stability ranking.

## Response format

shortlist: Sample_..., Sample_..., Sample_..., Sample_..., Sample_..., Sample_...
ranking: Sample_... > Sample_... > Sample_... > Sample_... > Sample_... > Sample_...
```

中文问题：

```text
# 找出被序列分化掩盖的稳定结构模拟物

`data/` 下的序列与坐标队列包含远缘变体、重排诱饵，以及锚定结构的真正结构模拟物。请找出六个候选：它们在序列相似性较弱的同时仍保留三维拓扑，因此二者之间呈现最强的正向不一致性；同时还要对破坏该队列保守结构核心的情况施加惩罚。随后，根据物理能量、溶剂暴露程度、模型置信度和二级结构组成之间的一致性，对这六个候选进行排序。请同时报告不要求顺序的六成员短名单及其最终稳定性排名。

## 输出格式

shortlist: Sample_..., Sample_..., Sample_..., Sample_..., Sample_..., Sample_...
ranking: Sample_... > Sample_... > Sample_... > Sample_... > Sample_... > Sample_...
```

答案：

```json
[
  {
    "expected": [
      "Sample_021",
      "Sample_017",
      "Sample_009",
      "Sample_002",
      "Sample_024",
      "Sample_004"
    ],
    "field": "discordant_shortlist",
    "kind": "unordered_set"
  },
  {
    "expected": [
      "Sample_009",
      "Sample_021",
      "Sample_002",
      "Sample_017",
      "Sample_024",
      "Sample_004"
    ],
    "field": "stability_ranking",
    "kind": "ranking",
    "require_complete": true
  }
]
```

Rubric：Credit requires shortlist Sample_021, Sample_017, Sample_009, Sample_002, Sample_024, Sample_004 and stability ranking Sample_009 > Sample_021 > Sample_002 > Sample_017 > Sample_024 > Sample_004

任务类型：`structural-discordance-cohort`（结构不一致性队列分析）

预期中，Agent 解决本问题需要调用的工具数：33
