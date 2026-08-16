from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
from conftest import FakeRuntime

from bio_mystery_synth.artifacts import ArtifactStore
from bio_mystery_synth.core import (
    AnswerSpec,
    Backend,
    Difficulty,
    ExactAssertion,
    ExecutionSpec,
    ExternalReferenceSourceSpec,
    FamilyConfig,
    FamilyResult,
    GroundTruth,
    OracleType,
    QuestionContext,
    ScenarioSpec,
)
from bio_mystery_synth.generation import CaseGenerator, validate_case
from bio_mystery_synth.task_families import FamilyRegistry
from bio_mystery_synth.tools import ToolDescriptor, ToolRegistry


class ExternalFixtureSpec(FamilyConfig):
    kind: Literal["external-fixture-mutation"] = "external-fixture-mutation"


class ExternalFixtureFamily:
    family_id = "external-fixture-mutation"
    config_model = ExternalFixtureSpec
    defaults = {difficulty: {} for difficulty in Difficulty}  # noqa: RUF012
    tools = ()
    supported_sources = ("external-reference",)

    def generate(self, spec: ScenarioSpec, context: object) -> FamilyResult:
        del spec
        asset = context.source.assets[0]
        reference = asset.path.read_text().splitlines()[1]
        mutated = reference[:4] + "T" + reference[5:]
        context.artifacts.write_bytes(
            "public",
            "data/reads.fastq",
            f"@Sample_001\n{mutated}\n+\n{'I' * len(mutated)}\n".encode(),
        )
        return FamilyResult(
            ground_truth=GroundTruth(
                oracle_type=OracleType.INJECTED,
                facts={"mutation": {"position": 5, "alternate": "T"}},
                anonymization_map={"raw_reference": "Sample_001"},
                evidence={"source_sha256": asset.sha256},
            ),
            answer=AnswerSpec(
                oracle_type=OracleType.INJECTED,
                assertions=[ExactAssertion(field="mutation", expected="5:T")],
                rubric_text="Credit requires the injected mutation 5:T.",
            ),
            question_context=QuestionContext(
                task_family=self.family_id,
                goal="Identify the injected change",
                public_files=["data/reads.fastq"],
                answer_format="mutation: position:base",
                default_question="Identify the single change represented by the anonymous reads.",
            ),
        )


def test_registries_accept_independent_extensions() -> None:
    family_registry = FamilyRegistry()
    family_registry.register(ExternalFixtureFamily)
    assert family_registry.get("external-fixture-mutation").config_model is ExternalFixtureSpec
    with pytest.raises(ValueError, match="duplicate task family"):
        family_registry.register(ExternalFixtureFamily)

    tool_registry = ToolRegistry()
    tool_registry.register(ToolDescriptor("fixture-tool", ("fixture",)))
    assert tool_registry.get("fixture-tool").groups == ("fixture",)


def test_artifact_store_supports_binary_files_and_guards_paths(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_bytes("public", "data/reads.fastq.gz", b"\x1f\x8bfixture")
    assert store.paths("public") == ["data/reads.fastq.gz"]
    with pytest.raises(ValueError, match="invalid artifact path"):
        store.write_text("public", "../private/answer.json", "leak")


def test_external_reference_injection_pipeline(tmp_path: Path) -> None:
    reference = tmp_path / "prepared-reference.fasta"
    reference.write_text(">fixture-reference\nAACCGGTTAACC\n")
    scenario = ScenarioSpec(
        schema_version="2",
        difficulty=Difficulty.EASY,
        seed=19,
        source=ExternalReferenceSourceSpec(
            provider="local-file",
            reference_id="fixture-reference",
            release="fixture-v1",
            parameters={"path": str(reference), "kind": "genome"},
        ),
        family=ExternalFixtureSpec(),
        execution=ExecutionSpec(backend=Backend.LOCAL, local_device="cpu"),
    )
    families = FamilyRegistry()
    families.register(ExternalFixtureFamily)
    generated = CaseGenerator(tmp_path, families=families).generate(
        scenario,
        runtime=FakeRuntime(19),
        case_id="case-external-fixture",
    )
    assert validate_case(generated.path, families=families) == []
    assert (generated.path / "public/data/reads.fastq").read_bytes().startswith(b"@Sample_001")
    source_manifest = (generated.path / "private/source_manifest.json").read_text()
    assert "fixture-reference" in source_manifest
    public = "\n".join(
        path.read_text(errors="ignore") for path in (generated.path / "public").rglob("*") if path.is_file()
    )
    assert "fixture-reference" not in public
    assert families.validate_scenario_json(scenario.model_dump_json()) == scenario
