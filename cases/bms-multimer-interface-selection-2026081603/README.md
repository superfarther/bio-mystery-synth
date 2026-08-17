### bms-multimer-interface-selection-2026081603

英文问题：

```text
# Prioritize sequence-diverse binders by coherent multimer interface evidence

`data/binders.fasta` contains a diverse synthetic binder panel for the protein in `data/target.fasta`. Rank the three most credible binders. A defensible ranking must account for sequence redundancy, the geometry of predicted two-chain assemblies, uncertainty both within and across the interface, local contact density, and overall model confidence. Treat apparent contacts unsupported by cross-chain confidence as decoys, and do not let a single headline score override contradictory interface evidence.

## Response format

top_three: Sample_... > Sample_... > Sample_...
```

中文问题：

```text
# 根据一致的多聚体界面证据对序列多样的结合蛋白进行优先级排序

`data/binders.fasta` 包含一组针对 `data/target.fasta` 中蛋白质的多样化合成结合蛋白。请对最可信的三个结合蛋白进行排序。可靠的排序必须考虑序列冗余、预测双链复合物的几何结构、界面内部及跨界面的不确定性、局部接触密度，以及模型的整体置信度。缺乏跨链置信度支持的表面接触应视为诱饵，且不能让某一个突出的汇总分数压过相互矛盾的界面证据。

## 输出格式

top_three: Sample_... > Sample_... > Sample_...
```

答案：

```json
[
  {
    "expected": [
      "Sample_001",
      "Sample_009",
      "Sample_008"
    ],
    "field": "top_three",
    "kind": "ranking",
    "require_complete": true
  }
]
```

Rubric：Credit requires the top three binders in order: Sample_001 > Sample_009 > Sample_008

任务类型：`multimer-interface-selection`（多聚体界面筛选）

预期中，Agent 解决本问题需要调用的工具数：27
