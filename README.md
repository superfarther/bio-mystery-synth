# bio-mystery-synth

## 数据生成 Pipeline

从输入配置到最终 case，数据会依次经过以下步骤：

```text
命令行参数 / YAML / 自然语言描述
                 │
                 ▼
         ScenarioSpec（出题配方）
                 │
                 ▼
       对应任务族的 generate 方法
        ├── proto-language 生成基础序列
        ├── 注入题目需要的信号或差异
        ├── 将内部名称替换成 Sample_...
        └── proto-tools 运行分析工具
                 │
                 ▼
              FamilyResult
        ├── 公开数据 ──────────► public/data/
        ├── 完整生成记录 ──────► private/latent_truth.json
        ├── 答案和Rubrics ────► private/answer.json
        └── 有限的出题上下文
                 │
                 ▼
        QuestionWriter（可选 LLM）
                 │
                 ▼
          public/question.md
                 │
                 ▼
       记录工具调用和文件校验值
                 │
                 ▼
           cases/<case_id>/
```

具体过程如下：

1. **确定出题配方**：CLI 根据题型、难度、seed 和运行后端创建 `ScenarioSpec`；使用 `--plan-prompt` 时，LLM 先把自然语言要求整理成同样的结构化配方。
2. **选择任务族**：程序根据 `family` 找到对应的生成逻辑。例如，不同任务族会决定要生成 DNA、RNA 还是蛋白质，以及要运行哪些分析工具。
3. **合成基础数据**：任务族调用 `proto-language` 生成满足长度、序列类型或 GC 含量要求的基础序列。所有解题数据都在当前 case 内生成和提供，这就是本项目所说的“闭世界”：Agent 不需要到外部数据库补充材料。
4. **预先确定答案来源**：程序会先选定正确样本、位置或变化，再把相应信号写入合成数据。例如，程序先决定把 motif 插入哪条序列的哪个坐标，并立即记录这个坐标；它不是生成完问题后再尝试从序列中猜答案。
5. **匿名化并构造答案**：生成阶段可能使用 `dna_001`、`protein_003` 这样的内部名称。公开前，它们会被打乱并替换为 `Sample_001`、`Sample_002` 等名称。对于依赖计算结果的题，程序会实际运行 `proto-tools`，再根据返回的命中位置、分数或排序构造答案。无论答案来自预先注入的真值，还是来自工具的实际输出，依据都会保存在 `latent_truth.json` 中。
6. **生成答案后，再写问题**：任务族先根据上述真值和计算结果创建的 `AnswerSpec`，其中已经明确写出标准答案所在的样本、坐标、数值范围或排序。完成这一步之后，程序才调用 `QuestionWriter` 撰写 `question.md`。传给 `QuestionWriter` 的只有题目目标、公开文件名、回答格式和默认题目文本，不包含 `AnswerSpec`、完整真值、内部名称或匿名化映射。因此，即使 `QuestionWriter` 使用 LLM，LLM 也看不到标准答案，更不负责生成标准答案。
7. **检查公开/私有边界**：写入文件前，程序会确认问题引用的文件与实际公开文件一致，并检查问题中没有出现 `dna_001` 这类内部名称。
8. **保存并记录生成过程**：结果写入 `public/` 和 `private/`，并保存本次使用的 seed、后端和工具调用记录。只有全部步骤成功后，完整 case 才会进入 `cases/`。

**需要特别注意：答案由隐藏真值或生物信息学专业工具决定。** 正确答案只有两种来源：一是程序在合成数据时主动注入并同步记录的隐藏真值；二是程序实际运行生物信息学专业工具后，从工具返回结果中确定的值。任务族据此先构造将写入 `answer.json` 的 `AnswerSpec`，随后才把不含答案的有限上下文交给 LLM 生成 Questions。LLM 可以规划“出什么题”和改写“题目怎么说”，但不决定标准答案是什么。

## 仓库布局

本项目依赖 `proto-language` 和 `proto-tools` 的本地源码。三个仓库必须位于同一个顶层目录下，名称保持如下：

```text
<workspace>/
├── proto-language/
├── proto-tools/
└── bio-mystery-synth/
```

生成数据时，本项目通过 `ProtoRuntime` 使用这两个仓库：

- `proto-language` 按照长度、序列类型和 GC 含量等要求，生成题目所需的 DNA、RNA 或蛋白质序列。
- `proto-tools` 对这些合成数据运行结构预测、序列比对、基因注释等工具，并记录每次调用使用的设备、参数和运行结果。
- `--backend local` 在当前机器执行工具；`--backend modal` 使用已有的 Proto Modal 部署。任务族本身不区分这两种后端。

运行生成命令前，应让 Python 优先导入顶层目录中的这两个仓库：

```bash
export BMS_WORKSPACE=/path/to/workspace
export PYTHONPATH="$BMS_WORKSPACE/proto-language:$BMS_WORKSPACE/proto-tools:${PYTHONPATH:-}"
```

## 环境配置

项目需要 Python 3.10 或更高版本。推荐使用项目约定的 Conda 环境：

```bash
conda create -n bio-mystery-synth python=3.11 pip -y
conda activate bio-mystery-synth
```

首次配置时，在三个仓库的共同顶层目录中按顺序安装本地源码：

```bash
proxy_off
python -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple -e ./proto-tools
python -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple --no-deps -e ./proto-language
python -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple -e "./bio-mystery-synth[dev,openai]"
```

先安装 `proto-tools`，再以 `--no-deps` 安装 `proto-language`，可以避免后者从远程地址安装另一份 `proto-tools`。最后安装本项目；若不需要 LLM 问题改写，可将最后一条命令中的 `[dev,openai]` 改为 `[dev]`。

建议将 Proto 的持久化内容放在独立缓存目录：

```bash
export PROTO_HOME=/path/to/resource/proto_home
export PROTO_MODEL_CACHE=/path/to/resource/proto_model_cache
```

`proto-tools` 不要求用户手工安装 micromamba 或逐个配置工具环境。某个隔离工具首次运行时，它会自动：

1. 将 micromamba 安装到 `$PROTO_HOME/.micromamba/`；
2. 创建共享的基础环境和该工具自己的隔离环境；
3. 安装与工具及当前硬件匹配的依赖；
4. 缓存环境和模型，使后续调用直接复用。

安装完成后可验证三个包和项目 CLI：

```bash
python -c "import proto_language, proto_tools, bio_mystery_synth"
bio-mystery-synth list-families
bio-mystery-synth list-tools
pytest
```

普通单元测试使用 `FakeRuntime`，不会启动真实的 Proto 模型环境。

## 工具目录

框架维护一个白名单，而不是把 proto-tools 注册表中的所有工具全部暴露给合成流程。当前包含 31 个可用工具：

| 能力链 | 新增工具 |
| --- | --- |
| 启动子与基因组上下文 | `promoter-calculator` |
| Profile 与局部同源分析 | `pyhmmer-hmmscan`、`pyhmmer-hmmsearch`、`pyhmmer-jackhmmer`、`pyhmmer-nhmmer`、`blast-create-db`、`blast-search`、`mmseqs2-clustering`、`mmseqs2-search-genomes` |
| 结构比较与分群 | `foldseek-cluster`、`foldseek-multimercluster`、`pymol-rmsd-alignment`、`usalign-alignment`、`dssp-secondary-structure` |
| 分子与界面分析 | `vina-docking`、`ipsae-scoring`、`pdockq2` |

`ProtoRuntime` 只允许目录内工具，继续拒绝整个 `database_retrieval` 类别。`blast-search` 会被强制设为本地模式，并且必须接收当前 case 内由 `blast-create-db` 建出的 `local_db`；传入在线模式会在工具执行前失败。

`list-tools` 会列出当前任务族、扩展能力组以及已安装 proto-tools 中可解析的工具总数：

```bash
$ bio-mystery-synth list-tools

dna-motif-localization: random-nucleotide-sample, meme-fimo-scan
rna-structure-ranking: random-nucleotide-sample, viennarna-prediction
protein-structure-nearest: random-protein-sample, esmfold-prediction, tmalign-alignment
protein-bridge-triage: random-protein-sample, esmfold-prediction, structure-metrics, tmalign-alignment, mafft-align
crispr-spacer-linkage: minced-crispr
windowed-recombination: mafft-align
utr-regulatory-assay: orfipy-prediction, miranda-scan, viennarna-prediction, primer3-thermodynamics
metagenomic-enzyme-forensics: prodigal-prediction, pyhmmer-phmmer, esmfold-prediction, structure-metrics, tmalign-alignment
[promoter-context]: promoter-calculator
[profile-and-local-homology]: pyhmmer-hmmscan, pyhmmer-hmmsearch, pyhmmer-jackhmmer, pyhmmer-nhmmer, blast-create-db, blast-search, mmseqs2-clustering, mmseqs2-search-genomes
[structure-comparison]: foldseek-cluster, foldseek-multimercluster, pymol-rmsd-alignment, usalign-alignment, dssp-secondary-structure
[molecular-interaction]: vina-docking, ipsae-scoring, pdockq2
31/31 tools available
```

当前机器准备扩展环境时，可将所有持久化依赖固定在共享资源目录：

```bash
export PROTO_HOME=/share/org/YZWL/yzwl_yuanzh/work/kimi-work/resource/proto_home
export PROTO_MODEL_CACHE=/share/org/YZWL/yzwl_yuanzh/work/kimi-work/resource/proto_model_cache
```

## 项目目录结构

```text
bio-mystery-synth/
├── cases/                    # 已生成并保留的 case
├── configs/                  # 批量生成配置示例
├── scripts/                  # 用于复现实验的 CPU/GPU 生成脚本
├── src/bio_mystery_synth/
│   ├── core/                 # Scenario、答案、真值和 manifest 模型
│   ├── generation/           # case 编排、校验和索引
│   ├── task_families/        # 任务族实现、配置与注册中心
│   ├── runtime/              # Runtime 接口与 Proto 后端
│   ├── tools/                # 独立工具目录和执行策略
│   ├── sources/              # 闭世界及外部参考数据源
│   ├── synthesis/            # 可复用干预和观测模拟接口
│   ├── artifacts/            # 文本、二进制和已有文件发布
│   ├── authoring/            # 场景规划和问题撰写
│   └── cli/                  # CLI 命令和配置模型
└── tests/                    # 模型、CLI、流水线和运行时测试
```

各目录职责如下：

- `task_families/`：每个任务族声明自己的配置模型、难度默认值、工具依赖和可用 source。注册中心是 CLI、场景解析和生成器的唯一任务族目录。
- `tools/`：工具白名单、能力分组和闭世界策略独立于任务族。任务族只通过 `Runtime` 调用工具，不区分 local 与 Modal。
- `sources/`：负责准备基础生物数据并记录来源；数据库检索不属于闭世界工具执行。
- `artifacts/`：统一发布文本、二进制或已有文件，并检查可见性和相对路径。
- 根目录下的 `models.py`、`pipeline.py`、`factory.py` 等旧入口继续提供兼容导出。
- `configs/`：存放 `batch` 命令使用的 YAML 配置示例。
- `scripts/`：存放固定 seed 和 case ID 的复现实验脚本，以及计算节点启动脚本。
- `tests/`：检查输入格式、CLI、公开/私有数据隔离，以及完整 case 的生成行为。
- `cases/`：保存生成成功的 case；其内部的 `public/` 与 `private/` 必须始终分离。

## 项目输入

无论使用命令行、自然语言还是 YAML，输入最终都会转换成一个 `ScenarioSpec`。可以把它理解为一张“出题配方”：它明确规定生成什么类型的题、生成多少数据、使用哪个随机种子，以及在哪种设备上运行工具。同一份配方可以重复生成和审计。

`ScenarioSpec` 主要包含：

- `family`：任务族及其专属参数；
- `difficulty`：`easy`、`medium` 或 `hard`；
- `seed`：控制数据合成和样本重命名的随机种子；
- `execution`：`local` 或 `modal` 后端、本地设备及工具参数覆盖；
- `anonymization`：把生成时使用的内部名称改成 `Sample_001` 这类公开名称时采用的规则；
- 可选的实体、约束、干预和观测描述。

CLI 支持三种输入方式。

### 使用默认场景生成一个 case

```bash
bio-mystery-synth generate \
  --family dna-motif-localization \
  --difficulty medium \
  --seed 1000 \
  --backend local \
  --local-device cpu \
  --output .
```

`generate` 根据 `family`、`difficulty`、`seed`、`backend` 和 `local-device` 构造默认 `ScenarioSpec`。未指定 `seed` 时会随机生成一个种子。`--output` 表示输出根目录，case 实际写入 `<output>/cases/`。

### 使用自然语言描述规划场景

```bash
export OPENAI_API_KEY=...
bio-mystery-synth generate \
  --family dna-motif-localization \
  --llm openai \
  --model <model> \
  --plan-prompt "生成一个中等难度、需要定位多个 DNA motif 的闭世界任务"
```

`--plan-prompt` 会让 LLM 在项目支持的题型和工具范围内生成结构化 `ScenarioSpec`。LLM 只负责提出出题方案和撰写问题，不会直接生成标准答案。标准答案由程序在合成数据时记录的已知结果，或由生物信息学工具的实际计算结果得到。

不传 `--plan-prompt` 时，`--llm openai --model <model>` 只改写公开问题；完全不使用 LLM 时省略这两个参数，生成器会采用任务族内置问题。

### 使用 YAML 批量生成

```bash
bio-mystery-synth batch --config configs/curriculum.example.yaml
```

批量配置由以下部分组成：

```yaml
output_root: output
max_workers: 1
llm:
  provider: none
jobs:
  - family: dna-motif-localization
    difficulty: easy
    count: 2
    seed: 1000
    backend: local
    local_device: cpu
```

每个 job 从 `seed` 开始连续生成 `count` 个场景；`max_workers` 控制并行数。

## 输出结构

生成数据保存在 `cases/`。每个 case 都分成两部分：`public/` 是交给 Agent 的题目包，`private/` 是用于复盘的内部记录。

```text
cases/<case_id>/
├── public/
│   ├── question.md
│   └── data/
│       └── ...
└── private/
    ├── scenario.json
    ├── answer.json
    ├── latent_truth.json
    └── generation_manifest.json
```

- `public/question.md`：交给 Agent 的题目，说明要完成什么分析、可以使用哪些数据，以及答案必须采用什么格式。
- `public/data/`：Agent 解题时需要分析的数据。这些数据完全由项目合成，样本名称已替换为 `Sample_...`。具体文件取决于任务族，可能是 FASTA、结构文件、motif 或表格。
- `private/scenario.json`：生成本题时使用的“出题配方”，包括题型、难度、seed、数据规模和运行后端。它可以用来确认这道题是怎样配置出来的。
- `private/answer.json`：该问题的标准答案和Rubrics。
- `private/latent_truth.json`：数据生成期间的隐藏真值。例如：motif 实际被插入了哪个位置、哪个候选项是特意构造的正确项、生成时的内部名称 `dna_002` 对应公开名称 `Sample_007`，以及分析工具返回的详细结果。这些信息用于追溯答案是怎么得到的。
- `private/generation_manifest.json`：本次生成的运行日志，记录 case ID、seed、执行后端、调用过的工具、公开文件列表和文件校验值，用于检查文件是否完整或被修改。

`public/` 是 Agent 在训练或评测时看到的全部内容；`private/` 只能用于审核和检查，不得交给 Agent。

## 扩展任务族、工具与数据源

新任务族实现 `generate(spec, context)`，并通过 `FamilyRegistry` 注册配置模型、默认参数、工具依赖和支持的数据源。`context` 提供 `Runtime`、`SourceBundle`、确定性随机数、`ArtifactStore` 以及干预/观测注册中心。新增任务族不需要修改 `ScenarioSpec` 的中央联合类型或 CLI 分支。

新工具通过 `ToolRegistry` 描述，并由 `ToolPolicy` 决定是否能在当前合成模式运行。默认 `ClosedWorldToolPolicy` 继续禁止 `database_retrieval`，并强制 BLAST 使用 case-local database。

外部参考场景使用 schema v2 的 `ExternalReferenceSourceSpec`。当前内置 `local-file` provider 用于消费登录节点预先准备并校验过的参考文件；后续 RefSeq、SRA、ENA 等 provider 应实现相同接口，把下载内容缓存在共享 resource 目录，再将带版本和 SHA-256 的 `SourceBundle` 交给任务族。来源 ID、缓存路径、注入事实和匿名化映射只写入 `private/`，外部参考 case 另有 `private/source_manifest.json`。
