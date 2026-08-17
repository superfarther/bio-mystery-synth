## BioMysteryBench-full

1. 这个bench的question是一个高难度的长程生物学问题，有标准答案。
2. Agent的输入是question，输出是对这个问题的探索结果。
3. 这个bench考察的是 Agent 自主解决困难长程问题的能力，而非简单的知识问答。
4. 评测方式为Rubrics。Rubrics 会检查 Agent 的最终答案是否满足标准答案，同时还会进行反作弊检查，验证Agent探索过程中是否通过 accession来源论文或研究元数据反向识别数据集。两项都通过即为正确。
5. 评测时，本地部署的工具（如AF2）基本可以随意使用，但是联网查询外部信息有限制，只能查询白名单规定的数据库。
6. 构造这个bench的信息源包括 NCBI GEO、SRA、ENA、BioProject、ArrayExpress 及其他类似的公共生物数据档案。可能会利用这些档案中的 DNA/RNA 测序 reads、基因表达矩阵、变异、表观基因组信号、蛋白质结构或质谱数据，以及与之关联的物种、组织、疾病、处理条件、敲除基因、感染状态等元数据。
7. 虽然没有公布具体的bench构造方式，但是大致可能是：人类专家从具有客观答案的真实生物数据出发，隐藏数据来源和原始标签，必要时进行人工数据改造，再围绕保留的真值设计定制问题、标准答案与评分规则。

## 解决思路

> 我们假设 Agent 已经具备基础的生物学知识，能够理解底层的生物学概念，换句话说，Agent 已经经过知识型的预训练、SFT 和 RL。如果发现 Agent 连基础的生物学知识都无法理解，那么首先需要针对性地进行知识训练。关于如何增强模型的生物学知识，可以参考我之前的工作：[GraphGen](https://github.com/InternScience/GraphGen) 和 [K2V](https://github.com/SeedScientist/K2V)。

1. BioMysteryBench-full 旨在评估 Agent 解决困难长程生物问题的能力，Agent 无法依靠模型自身的内部知识直接回答这些问题，只能通过缜密思考，正确调用多种不同工具，且具备长时稳定运行的能力才有可能解决这些问题。
2. 为了提高 Agent 在BioMysteryBench-full上的精度，可以对症下药，针对性地在生物场景中合成必须经过长程思考与工具调用才能解决的问题。具体地说，预期中我们可以搭建一个数据合成pipleline，如果 Agent 想要解决这些问题，必须经过缜密的长程思考，正确调用多种不同工具，识别自身错误并及时纠错。也就是像解决 BioMysteryBench-full 那样，训练 Agent 形成**推理、决策、工具调用、反思、纠错的长程循环**。
3. 为了能够批量合成大规模的数据，我们可以**利用 LLM 模仿人类专家构造 BioMysteryBench-full 的思路**。具体地说，可以驱动 LLM 在某种背景设定下，合理地调用多种不同的生物学专业工具，构造出一个必须经过多轮长程工具调用才能得到的问答对。
4. **答案的可验证性很重要**，必须确保合成出来的问题具备唯一且可验证的答案，否则很容易发生reward hacking。
5. **推理过程的可验证性也很重要**（实际上是信用分配问题），这个问题大致有三种解法：

   1. 借鉴 SAO 的思路，回归经典PPO，训练一个 value model
   2. 参考一些 GRPO 类工作的信用分配思路
   3. 本方法合成数据时本身就必须调用多种不同的工具，这很自然地形成了一条长程工具调用链，而这个工具链或许可以作为一种推理过程的标准答案（不唯一，因为通往正确结果的路径可能不只有这一个）

## 方法

本方法合成数据时依赖 [proto-language](https://github.com/evo-design/proto-language) 和 [proto-tools](https://github.com/evo-design/proto-tools)。

### Proto-language

1. 一个使用Python代码描述生物序列与结构设计需求的框架。用户可以定义待设计的 DNA、RNA 或蛋白质区域，以及长度、组成、结构、活性、等目标约束。
2. 输入是 Python 程序，以及可选的初始序列、目标结构、配体和设计参数；输出包括候选生物序列、预测结构、约束评分、优化历史、FASTA 和结果表格等。
3. 对于生物学中的序列或结构生成任务，可以组织起来一个 生成候选—工具评估—筛选—继续优化 的设计循环。
4. proto-language主要负责设计任务的表达、工具编排和优化搜索，本身不是生物模型集合。复杂的序列生成、结构预测和功能评分通常由proto-tools执行。
5. 优化结果是模型在有限计算预算内找到的较优候选，不能保证一定满足真实生物学目标，仍需要独立计算验证和实验验证。

### Proto-tools

1. 集成了众多计算生物学工具和生物 AI 模型，包括 AlphaFold2/3、Boltz2、ESMFold、RFdiffusion3、ProteinMPNN、LigandMPNN、MMseqs2、BLAST、MAFFT、AlphaGenome 和 Enformer 等。
2. 以MCP的形式为不同工具封装了Python接口，基本调用形式为 工具 + 配置 → 运行工具 → 工具输出。
3. 工具既可以在本地 CPU/GPU 上运行，也可以通过 Modal 在远程计算资源上运行，并提供 GPU 分配、批处理、并行执行和模型常驻等能力。
4. proto-tools可以作为独立 Python 库使用，也可以作为proto-language的底层执行层，还可以启动为 MCP Server，直接向 Agent 暴露生物工具。

**Proto-language和Proto-tools的关系可以概括为：**

proto-language：用python代码的形式描述“生物任务中设计什么、什么结果算好、如何迭代优化”

↓

proto-tools：执行“生成、预测、比对、注释和评分”

↓

输出：候选序列、预测结构、评分和优化记录

### 无外部信息源的数据合成方案

**无外部信息源是指，建立题目场景时，初始的生物学数据来自于本地模型自己生成，而非查询外部生物数据库（如SRA、ENA和BioProject）**

**之所以当前版本的 bio-mystery-synth 无外部信息源，是因为外部数据库的数据格式不统一，需要针对性地撰写数据清洗脚本，耗时较长（正在实现ing）。**

对于无外部信息源的方案，一条数据从任务设想到最终发布，大体经过四个阶段。

**第一，确定题目背景和难度**。系统先决定要研究哪类生物对象、提供多少候选、序列有多长、隐藏多少目标以及加入多少干扰项。。

**第二，生成基础数据并写入隐藏事实**。基础 DNA、RNA 或蛋白质序列由 Proto-language 生成，随后再按照题目需要加入特定信号。例如，DNA motif 任务会把目标 motif 写入指定序列，同时加入只差一个碱基的干扰项；CRISPR 任务会把能够连接宿主和噬菌体的 spacer 写入部分宿主基因组；重组任务会把来自两个参考分支的片段拼接成嵌合序列。写入信号的同时，系统立即保存正确样本和正确位置，不需要在出题以后再猜答案，隐藏事实就是标准答案。

**第三，多步真实的专业生物学工具计算**。RNA 结构任务需要预测二级结构，再比较候选与参考结构的相似度；蛋白质结构任务需要预测三维结构，再进行结构比对和排序。更长的任务会把多种工具调用串起来：蛋白质桥接任务同时比较候选与两个锚点的结构和序列特征；UTR 调控任务综合编码区完整性、miRNA 位点、局部结构和引物性质；宏基因组酶任务综合基因位置、同源性、序列完整性、组成偏差和结构证据。每一步都缩小候选范围，但只有完成整条工具链才能确定答案。

**第四，固定答案并生成问题**。系统根据隐藏事实或记录下来的计算结果生成标准答案和评分要求，再把内部样本名随机替换为 `Sample_...`。之后才生成问题和 Agent 要分析的数据。

这套方法把人类专家设计 BioMysteryBench-full 的思路拆成了可以重复执行的流程：先确定客观事实，再合成数据和干扰项，通过调用多种生物专业工具，最后从已经确定的答案出发撰写问题。它既利用 LLM 扩展题目背景和表达方式，又把答案决定权留给生物工具计算过程，从而支持批量构造长程、多步骤、可验证的生物信息学训练任务。

## 强化学习环境搭建

Agent 训练时可以通过 MCP 轻松地接入proto-tools，调用生物专业工具，因此搭建训练环境的方向很明确。出于时间限制，当前初始版本未实现。

## Cases 分析

本节对 bio-mystery-synth 合成出来的十条困难长程数据进行分析。

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
