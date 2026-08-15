"""Case generation and validation."""

from __future__ import annotations

import json
import secrets
import shutil
from pathlib import Path

from bio_mystery_synth.llm import QuestionWriter
from bio_mystery_synth.models import (
    AnswerSpec,
    CaseIndexEntry,
    GeneratedCase,
    GenerationManifest,
    GroundTruth,
    ScenarioSpec,
)
from bio_mystery_synth.runtime import DECLARED_TOOLS, ProtoRuntime, Runtime
from bio_mystery_synth.sources import ClosedWorldSource
from bio_mystery_synth.task_families import get_family
from bio_mystery_synth.utils import dump_json, sha256


class CaseGenerator:
    def __init__(self, output_root: Path, question_writer: QuestionWriter | None = None) -> None:
        self.output_root = output_root.resolve()
        self.question_writer = question_writer or QuestionWriter()

    def generate(
        self,
        spec: ScenarioSpec,
        runtime: Runtime | None = None,
        case_id: str | None = None,
    ) -> GeneratedCase:
        ClosedWorldSource().materialize(spec)
        case_id = case_id or f"bms-{spec.task_family}-{secrets.token_hex(6)}"
        cases = self.output_root / "cases"
        stage = self.output_root / ".staging" / case_id
        target = cases / case_id
        if target.exists() or stage.exists():
            raise FileExistsError(case_id)
        stage.mkdir(parents=True)
        runtime = runtime or ProtoRuntime(spec.execution)
        try:
            result = get_family(spec.task_family).generate(spec, runtime, stage)
            public = stage / "public"
            private = stage / "private"
            for relative, content in result.public_files.items():
                self._write(public / relative, content)
            draft = self.question_writer.write(result.question_context)
            if set(draft.referenced_files) != set(result.public_files):
                raise ValueError("question references do not match the public data inventory")
            question = f"# {draft.title}\n\n{draft.prompt}\n\n## Response format\n\n{draft.expected_response_format}\n"
            private_tokens = result.ground_truth.anonymization_map.keys()
            if any(token in question for token in private_tokens):
                raise ValueError("question leaks a private identifier")
            self._write(public / "question.md", question)
            self._write(private / "answer.json", dump_json(result.answer))
            self._write(private / "latent_truth.json", dump_json(result.ground_truth))
            self._write(private / "scenario.json", dump_json(spec))
            files = sorted(path for path in stage.rglob("*") if path.is_file())
            hashes = {str(path.relative_to(stage)): sha256(path) for path in files}
            manifest = GenerationManifest(
                case_id=case_id,
                status="complete",
                seed=spec.seed,
                backend=spec.execution.backend,
                tool_calls=runtime.calls,
                public_files=sorted(["public/question.md", *(f"public/{path}" for path in result.public_files)]),
                file_sha256=hashes,
            )
            self._write(private / "generation_manifest.json", dump_json(manifest))
            cases.mkdir(parents=True, exist_ok=True)
            stage.replace(target)
        except Exception:
            failed = self.output_root / ".failed" / case_id
            failed.parent.mkdir(parents=True, exist_ok=True)
            if stage.exists():
                stage.replace(failed)
            raise
        index = CaseIndexEntry(
            case_id=case_id,
            task_family=spec.task_family,
            difficulty=spec.difficulty,
            seed=spec.seed,
            backend=spec.execution.backend,
            tools=sorted({record.tool for record in runtime.calls}),
            public_path=str(target / "public"),
            answer_path=str(target / "private" / "answer.json"),
        )
        return GeneratedCase(case_id=case_id, path=target, index=index)

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def validate_case(case_path: Path) -> list[str]:
    errors: list[str] = []
    public = case_path / "public"
    private = case_path / "private"
    required = [
        public / "question.md",
        private / "answer.json",
        private / "latent_truth.json",
        private / "scenario.json",
        private / "generation_manifest.json",
    ]
    errors.extend(f"missing {path.relative_to(case_path)}" for path in required if not path.is_file())
    if errors:
        return errors
    try:
        answer = AnswerSpec.model_validate_json((private / "answer.json").read_text())
        truth = GroundTruth.model_validate_json((private / "latent_truth.json").read_text())
        scenario = ScenarioSpec.model_validate_json((private / "scenario.json").read_text())
        manifest = GenerationManifest.model_validate_json((private / "generation_manifest.json").read_text())
    except Exception as exc:
        return [f"invalid private model: {exc}"]
    if answer.oracle_type != truth.oracle_type:
        errors.append("answer and truth oracle types differ")
    if scenario.task_family not in DECLARED_TOOLS:
        errors.append("unknown scenario family")
    public_text = "\n".join(path.read_text(errors="ignore") for path in public.rglob("*") if path.is_file())
    for raw_id in truth.anonymization_map:
        if raw_id in public_text:
            errors.append(f"public data leaks {raw_id}")
    for relative, expected in manifest.file_sha256.items():
        path = case_path / relative
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"hash mismatch: {relative}")
    return errors


def write_index(output_root: Path, entries: list[CaseIndexEntry]) -> Path:
    path = output_root / "index.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(entry.model_dump(mode="json"), sort_keys=True) + "\n" for entry in entries)
    path.write_text(text)
    return path


def clean_staging(output_root: Path) -> None:
    stage = output_root / ".staging"
    if stage.exists() and not any(stage.iterdir()):
        shutil.rmtree(stage)
