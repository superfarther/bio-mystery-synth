### bms-autonomous-utr-assay-20260822

英文问题：

```text
# Resolve a hidden UTR regulatory event and its diagnostic assay

The anonymous records in `data/transcripts.fasta` are competing synthetic isoforms. Exactly one combines an intact long coding region with a near-perfect site for a sequence in `data/mirnas.fasta` that lies in the resulting 3' UTR and is the most locally exposed in the minimum-free-energy fold. Identify that isoform and miRNA. Then choose, from `data/primer_pairs.tsv`, the matching diagnostic pair with closely balanced melting behavior near 60 °C and the weakest combined hairpin, self-dimer, and cross-dimer liabilities. Reconcile all evidence rather than treating a sequence match alone as sufficient.

## Response format

sample: Sample_...
miRNA: miR_SYN_...
primer_pair: Pair_...
```

中文问题：

```text
# 解析隐藏的 UTR 调控事件及其诊断检测方案

`data/transcripts.fasta` 中的匿名记录是相互竞争的合成异构体。其中恰有一个异构体同时具备完整的长编码区，以及一个与 `data/mirnas.fasta` 中某条序列近乎完全匹配的位点；该位点位于由此形成的 3' UTR 中，并且在最小自由能折叠结构中具有最高的局部暴露程度。请识别该异构体及对应的 miRNA。随后，从 `data/primer_pairs.tsv` 中选择与之匹配的诊断引物对：其在约 60 °C 附近的熔解行为应高度平衡，并且发卡、自二聚体和交叉二聚体三类风险的综合程度最低。必须综合全部证据，不能仅凭序列匹配得出结论。

## 输出格式

sample: Sample_...
miRNA: miR_SYN_...
primer_pair: Pair_...
```

答案：

```json
[
  {
    "case_sensitive": false,
    "expected": "Sample_014",
    "field": "sample",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "miR_SYN_01",
    "field": "mirna",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "Pair_01_04",
    "field": "primer_pair",
    "kind": "exact"
  }
]
```

Rubric：Credit requires Sample_014, miR_SYN_01, and Pair_01_04.

任务类型：`utr-regulatory-assay`（UTR 调控检测）

预期中，Agent 解决本问题需要调用的工具数：7
