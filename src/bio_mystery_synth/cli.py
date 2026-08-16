"""Command-line interface."""

from __future__ import annotations

import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Annotated, Literal

import typer
import yaml
from pydantic import Field

from bio_mystery_synth.factory import default_scenario
from bio_mystery_synth.llm import OpenAILLMClient, QuestionWriter, ScenarioPlanner
from bio_mystery_synth.models import Backend, CaseIndexEntry, Difficulty, ScenarioSpec, StrictModel
from bio_mystery_synth.pipeline import CaseGenerator, validate_case, write_index
from bio_mystery_synth.runtime import DECLARED_TOOLS, capability_catalog

app = typer.Typer(no_args_is_help=True)


class BatchJob(StrictModel):
    family: str
    difficulty: Difficulty = Difficulty.MEDIUM
    count: int = Field(default=1, ge=1)
    seed: int = Field(default=0, ge=0)
    backend: Backend = Backend.LOCAL
    local_device: str = "cuda"


class LLMSettings(StrictModel):
    provider: Literal["none", "openai"] = "none"
    model: str | None = None


class BatchConfig(StrictModel):
    output_root: Path = Path(".")
    max_workers: int = Field(default=1, ge=1)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    jobs: list[BatchJob]


def _writer(provider: str, model: str | None) -> QuestionWriter:
    if provider == "none":
        return QuestionWriter()
    if provider != "openai":
        raise typer.BadParameter(f"unsupported LLM provider: {provider}")
    if not model:
        raise typer.BadParameter("--model is required with --llm openai")
    return QuestionWriter(OpenAILLMClient(model))


@app.command()
def generate(
    family: Annotated[str, typer.Option()],
    difficulty: Annotated[Difficulty, typer.Option()] = Difficulty.MEDIUM,
    backend: Annotated[Backend, typer.Option()] = Backend.LOCAL,
    seed: Annotated[int | None, typer.Option()] = None,
    output: Annotated[Path, typer.Option()] = Path("."),
    local_device: Annotated[str, typer.Option()] = "cuda",
    llm: Annotated[Literal["none", "openai"], typer.Option()] = "none",
    model: Annotated[str | None, typer.Option()] = None,
    plan_prompt: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Generate one case."""
    seed = seed if seed is not None else secrets.randbits(31)
    writer = _writer(llm, model)
    if plan_prompt:
        if writer.client is None:
            raise typer.BadParameter("--plan-prompt requires an LLM")
        spec = ScenarioPlanner(writer.client).plan(plan_prompt)
    else:
        spec = default_scenario(family, difficulty, seed, backend, local_device)
    generated = CaseGenerator(output, writer).generate(spec)
    write_index(output, [generated.index])
    typer.echo(generated.path)


@app.command()
def batch(config: Annotated[Path, typer.Option(exists=True, dir_okay=False)]) -> None:
    """Generate cases from a curriculum YAML file."""
    settings = BatchConfig.model_validate(yaml.safe_load(config.read_text()))
    writer = _writer(settings.llm.provider, settings.llm.model)
    requests = [
        default_scenario(job.family, job.difficulty, job.seed + offset, job.backend, job.local_device)
        for job in settings.jobs
        for offset in range(job.count)
    ]

    def run(spec: ScenarioSpec) -> CaseIndexEntry:
        return CaseGenerator(settings.output_root, writer).generate(spec).index

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        entries = list(executor.map(run, requests))
    index = write_index(settings.output_root, entries)
    typer.echo(index)


@app.command("list-families")
def list_families() -> None:
    for family in sorted(DECLARED_TOOLS):
        typer.echo(family)


@app.command("list-tools")
def list_tools() -> None:
    catalog = capability_catalog()
    for family, tools in catalog["families"].items():
        typer.echo(f"{family}: {', '.join(tools)}")
    for group, tools in catalog["tool_groups"].items():
        typer.echo(f"[{group}]: {', '.join(tools)}")
    typer.echo(f"{len(catalog['tools'])}/{catalog['declared_tool_count']} tools available")


@app.command("validate")
def validate_command(case: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    errors = validate_case(case)
    if errors:
        for error in errors:
            typer.echo(error, err=True)
        raise typer.Exit(1)
    typer.echo("valid")
