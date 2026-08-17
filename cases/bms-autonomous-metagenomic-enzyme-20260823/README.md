### bms-autonomous-metagenomic-enzyme-20260823

英文问题：

```text
# Find the intact enzyme-family member hidden in anonymous metagenomic contigs

`data/contigs.fasta` contains synthetic metagenomic fragments with truncated genes, compositionally biased mimics, and several divergent relatives of the protein in `data/family_marker.fasta`. Identify the single most credible intact family member and its 1-based inclusive coding interval, including the terminal stop codon when present. A defensible call must reconcile prokaryotic gene boundaries, statistically meaningful full-length homology, low compositional bias, and a compact, high-confidence predicted fold; no one signal is sufficient on its own.

## Response format

sample: Sample_...
orf_interval: start-end
```

中文问题：

```text
# 找出隐藏在匿名宏基因组 contig 中的完整酶家族成员

`data/contigs.fasta` 包含合成的宏基因组片段，其中混有截短基因、具有组成偏差的模拟序列，以及 `data/family_marker.fasta` 中蛋白质的若干远缘亲属。请找出唯一最可信的完整家族成员，并给出其以 1 为起点、两端均包含在内的编码区间；若存在末端终止密码子，也应将其纳入区间。可靠的判断必须综合考虑原核基因边界、具有统计学意义的全长同源性、较低的组成偏差，以及紧凑且高置信度的预测折叠；任何单一信号都不足以独立得出结论。

## 输出格式

sample: Sample_...
orf_interval: start-end
```

答案：

```json
[
  {
    "case_sensitive": false,
    "expected": "Sample_012",
    "field": "sample",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "2079-2621",
    "field": "orf_interval",
    "kind": "exact"
  }
]
```

Rubric：Credit requires Sample_012 and ORF interval 2079-2621.

任务类型：`metagenomic-enzyme-forensics`（宏基因组酶取证）

预期中，Agent 解决本问题需要调用的工具数：11
