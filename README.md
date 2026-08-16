# bio-mystery-synth

Closed-world generation of bioinformatics mystery tasks using `proto-language` and
`proto-tools`. Generated cases separate public task data from private truth and grading
artifacts.

## Development setup

For data generation, make the existing Proto checkouts importable without installing
their optional model environments:

```bash
export PYTHONPATH="../proto/proto-language:../proto/proto-tools:$PYTHONPATH"
```

Local protein structure generation requires a configured local GPU. Use `--backend
modal` to dispatch expensive tools through the existing Proto Modal deployment.

## CLI

```bash
bio-mystery-synth list-families
bio-mystery-synth list-tools
bio-mystery-synth generate --family dna-motif-localization --backend local
bio-mystery-synth generate --family protein-structure-nearest --backend modal
bio-mystery-synth batch --config configs/curriculum.example.yaml
bio-mystery-synth validate cases/<case_id>
```

Set `OPENAI_API_KEY` and pass `--llm openai --model <model>` to use the OpenAI
structured-output question writer. Without it, the deterministic family question is used.

The `utr-regulatory-assay` and `metagenomic-enzyme-forensics` families are designed
for autonomous long-horizon solving: their public questions state biological goals and
evidence requirements without prescribing tool names, parameters, or call order.
