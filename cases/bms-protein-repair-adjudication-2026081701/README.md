### bms-protein-repair-adjudication-2026081701

英文问题：

```text
# Prioritize repaired proteins across sequence, sensitivity, fold, and stability evidence

The anonymous repair panel, its common reference, and corresponding coordinate models are under `data/`. Rank the five repairs most likely to restore a robust member of the reference family. Reconcile whole-sequence plausibility, representation-space proximity, sensitivity of the reference sequence landscape, preservation of the global fold and secondary-structure balance, whole-structure physical energy, and burial of sensitive sites. A candidate that excels on only one evidence class should not outrank a consistently supported repair.

## Response format

top_five: Sample_... > Sample_... > Sample_... > Sample_... > Sample_...
```

中文问题：

```text
# 综合序列、敏感性、折叠和稳定性证据对修复蛋白进行优先级排序

匿名修复候选集合、它们共用的参考蛋白，以及相应的坐标模型均位于 `data/` 下。请对最有可能恢复为参考家族中稳健成员的五个修复候选进行排序。判断时需要综合全序列合理性、表征空间接近性、参考序列景观中的敏感性、整体折叠与二级结构平衡的保持程度、全结构物理能量，以及敏感位点的埋藏程度。仅在某一类证据上表现出色的候选，不应排在得到多类证据一致支持的修复候选之前。

## 输出格式

top_five: Sample_... > Sample_... > Sample_... > Sample_... > Sample_...
```

答案：

```json
[
  {
    "expected": [
      "Sample_002",
      "Sample_003",
      "Sample_006",
      "Sample_009",
      "Sample_014"
    ],
    "field": "top_five_repairs",
    "kind": "ranking",
    "require_complete": true
  }
]
```

Rubric：Credit requires the five best repairs in order: Sample_002 > Sample_003 > Sample_006 > Sample_009 > Sample_014

任务类型：`protein-repair-adjudication`（蛋白质修复裁决）

预期中，Agent 解决本问题需要调用的工具数：41
