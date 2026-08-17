### bms-mobile-element-attribution-2026081605

英文问题：

```text
# Attribute a complete mobile element to its host and recover its boundaries

The anonymous sequences in `data/host_genomes.fasta` contain partial insertions, reversed decoys, rearranged boundary fragments, and one complete mobile element. Use the three probes in `data/boundary_probes.fasta` together with the expected cargo family in `data/cargo_marker.fasta` to identify the true host, the 1-based inclusive element interval, and its orientation. The accepted call must reconcile broad nucleotide homology, exact local boundary order, strand, element completeness, and an intact cargo coding region.

## Response format

host: Sample_...
element_interval: start-end
orientation: + or -
```

中文问题：

```text
# 判定完整可移动元件的宿主归属并恢复其边界

`data/host_genomes.fasta` 中的匿名序列包含不完整插入、反向诱饵、重排的边界片段，以及一个完整的可移动元件。请结合 `data/boundary_probes.fasta` 中的三个探针与 `data/cargo_marker.fasta` 中预期的货物基因家族，识别真实宿主、该元件以 1 为起点且两端均包含在内的区间，以及其方向。可接受的判断必须同时符合广泛的核苷酸同源性、精确的局部边界顺序、链方向、元件完整性，以及完整货物编码区等证据。

## 输出格式

host: Sample_...
element_interval: start-end
orientation: + or -
```

答案：

```json
[
  {
    "case_sensitive": false,
    "expected": "Sample_008",
    "field": "host",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "4001-5700",
    "field": "element_interval",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "+",
    "field": "orientation",
    "kind": "exact"
  }
]
```

Rubric：Credit requires host Sample_008, interval 4001-5700, and forward orientation.

任务类型：`mobile-element-attribution`（可移动元件归属判定）

预期中，Agent 解决本问题需要调用的工具数：8
