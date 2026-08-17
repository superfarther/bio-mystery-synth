### bms-promoter-cassette-forensics-2026081601

英文问题：

```text
# Resolve the expressed intact member of a divergent synthetic cassette family

The anonymous DNA cassettes in `data/cassettes.fasta` contain unrelated background, partial relatives, strand decoys, and several divergent members of the family represented by `data/family_marker.fasta`. Identify the single cassette that combines a complete coding region with the strongest plausible forward bacterial promoter immediately upstream. Report the 1-based transcription start and the 1-based inclusive coding interval, including the terminal stop codon. Sequence similarity, gene boundaries, strand, and promoter strength must agree; no one signal is decisive by itself.

## Response format

sample: Sample_...
tss: integer
orf_interval: start-end
```

中文问题：

```text
# 识别分化合成基因盒家族中能够表达的完整成员

`data/cassettes.fasta` 中的匿名 DNA 基因盒包含无关背景序列、不完整的亲属序列、链方向诱饵，以及 `data/family_marker.fasta` 所代表家族的若干远缘成员。请找出唯一一个同时具备完整编码区，并在其紧邻上游具有最强且合理的正向细菌启动子的基因盒。报告以 1 为起点的转录起始位点，以及同样以 1 为起点、两端均包含在内且包含末端终止密码子的编码区间。序列相似性、基因边界、链方向和启动子强度必须相互一致；任何单一信号都不能独立决定结论。

## 输出格式

sample: Sample_...
tss: integer
orf_interval: start-end
```

答案：

```json
[
  {
    "case_sensitive": false,
    "expected": "Sample_009",
    "field": "sample",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": 1690,
    "field": "tss",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "1811-2263",
    "field": "orf_interval",
    "kind": "exact"
  }
]
```

Rubric：Credit requires Sample_009, TSS 1690, and ORF interval 1811-2263.

任务类型：`promoter-cassette-forensics`（启动子基因盒取证）

预期中，Agent 解决本问题需要调用的工具数：6
