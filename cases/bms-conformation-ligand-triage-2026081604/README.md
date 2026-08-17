### bms-conformation-ligand-triage-2026081604

英文问题：

```text
# Select a fold-preserving receptor state and its best-supported ligand

The structures under `data/receptor_candidates/` are anonymous sequence variants of the state represented by `data/reference_state.pdb`; their sequences are in `data/receptor_sequences.fasta`. Select the variant that best preserves the global fold, backbone geometry, secondary-structure balance, and model confidence. Then evaluate the closed ligand panel in `data/compounds.tsv` against `data/binding_scaffold.pdb` at the residue-defined site in `data/site_residues.tsv` and identify the compound with the strongest pose support. Report the receptor and compound only after reconciling both the conformational and binding evidence.

## Response format

receptor: Sample_...
compound: Compound_...
```

中文问题：

```text
# 选择能够保持折叠的受体状态及证据支持最充分的配体

`data/receptor_candidates/` 下的结构是 `data/reference_state.pdb` 所代表状态的匿名序列变体，其序列位于 `data/receptor_sequences.fasta` 中。请选择在整体折叠、主链几何、二级结构平衡和模型置信度方面保持得最好的变体。随后，在 `data/site_residues.tsv` 以残基定义的位点处，使用 `data/binding_scaffold.pdb` 评估 `data/compounds.tsv` 中的封闭配体集合，并找出其结合姿势获得最强证据支持的化合物。只有在综合构象证据和结合证据后，才能报告受体与化合物。

## 输出格式

receptor: Sample_...
compound: Compound_...
```

答案：

```json
[
  {
    "case_sensitive": false,
    "expected": "Sample_001",
    "field": "receptor",
    "kind": "exact"
  },
  {
    "case_sensitive": false,
    "expected": "Compound_01",
    "field": "compound",
    "kind": "exact"
  }
]
```

Rubric：Credit requires receptor Sample_001 and ligand Compound_01.

任务类型：`conformation-ligand-triage`（构象—配体筛选）

预期中，Agent 解决本问题需要调用的工具数：17
