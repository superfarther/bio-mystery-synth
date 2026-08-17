### bms-metagenomic-stability-forensics-2026081703

英文问题：

```text
# Recover and rank stable enzyme-family members from a large anonymous metagenome

Search the complete anonymous contig collection under `data/` for intact relatives of the supplied synthetic family marker. Exclude truncated, compositionally biased, and rearranged mimics. From the remaining full-length relatives, report the three best-supported sample and 1-based inclusive coding intervals in order. The ranking must reconcile gene-boundary and homology evidence with whole-sequence plausibility, family-space proximity, conserved fold and secondary structure, physical energy, solvent exposure, and coordinate confidence; isolated evidence is insufficient.

## Response format

top_three: Sample_...:start-end > Sample_...:start-end > Sample_...:start-end
```

中文问题：

```text
# 从大型匿名宏基因组中恢复稳定的酶家族成员并进行排序

在 `data/` 下完整的匿名 contig 集合中搜索所提供合成家族标记的完整亲属，并排除截短、具有组成偏差或发生重排的模拟序列。从剩余的全长亲属中，按顺序报告证据支持最充分的三个样本及其以 1 为起点、两端均包含在内的编码区间。排序必须综合基因边界与同源性证据、全序列合理性、家族空间接近性、折叠与二级结构的保守程度、物理能量、溶剂暴露程度和坐标置信度；孤立的单项证据不足以支持结论。

## 输出格式

top_three: Sample_...:start-end > Sample_...:start-end > Sample_...:start-end
```

答案：

```json
[
  {
    "expected": [
      "Sample_103:3033-3695",
      "Sample_025:7588-8250",
      "Sample_124:1211-1873"
    ],
    "field": "top_three_orfs",
    "kind": "ranking",
    "require_complete": true
  }
]
```

Rubric：Credit requires the top three sample/ORF calls in order: Sample_103:3033-3695 > Sample_025:7588-8250 > Sample_124:1211-1873

任务类型：`metagenomic-stability-forensics`（宏基因组稳定性取证）

预期中，Agent 解决本问题需要调用的工具数：21
