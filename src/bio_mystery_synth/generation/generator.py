from __future__ import annotations

import random
import secrets
from pathlib import Path

from bio_mystery_synth.artifacts import ArtifactStore
from bio_mystery_synth.authoring import QuestionWriter
from bio_mystery_synth.core import (
    CaseIndexEntry,
    GeneratedCase,
    GenerationManifest,
    ScenarioSpec,
    SourceAssetRecord,
    SourceManifest,
)
from bio_mystery_synth.generation.context import GenerationContext
from bio_mystery_synth.runtime import ProtoRuntime, Runtime
from bio_mystery_synth.sources import materialize_source
from bio_mystery_synth.support import dump_json, sha256
from bio_mystery_synth.synthesis import SynthesisRegistry
from bio_mystery_synth.task_families.registry import FamilyRegistry, builtin_family_registry


class CaseGenerator:
    def __init__(
        self,
        output_root: Path,
        question_writer: QuestionWriter | None = None,
        synthesis: SynthesisRegistry | None = None,
        families: FamilyRegistry | None = None,
    ) -> None:
        self.output_root = output_root.resolve()
        self.question_writer = question_writer or QuestionWriter()
        self.synthesis = synthesis or SynthesisRegistry()
        self.families = families or builtin_family_registry()

    def generate(
        self,
        spec: ScenarioSpec,
        runtime: Runtime | None = None,
        case_id: str | None = None,
    ) -> GeneratedCase:
        case_id = case_id or f"bms-{spec.task_family}-{secrets.token_hex(6)}"
        cases = self.output_root / "cases"
        stage = self.output_root / ".staging" / case_id
        target = cases / case_id
        if target.exists() or stage.exists():
            raise FileExistsError(case_id)
        stage.mkdir(parents=True)
        artifacts = ArtifactStore(stage)
        runtime = runtime or ProtoRuntime(spec.execution)
        try:
            source = materialize_source(spec, stage / "source")
            definition = self.families.get(spec.task_family)
            if source.source_kind not in definition.supported_sources:
                raise ValueError(f"{spec.task_family} does not support source {source.source_kind}")
            context = GenerationContext(
                runtime=runtime,
                workspace=stage,
                source=source,
                artifacts=artifacts,
                rng=random.Random(spec.seed),
                synthesis=self.synthesis,
            )
            result = definition.generator.generate(spec, context)
            for relative, content in result.public_files.items():
                artifacts.write_text("public", relative, content)
            public_files = artifacts.paths("public")
            draft = self.question_writer.write(result.question_context)
            if set(draft.referenced_files) != set(public_files):
                raise ValueError("question references do not match the public data inventory")
            question = f"# {draft.title}\n\n{draft.prompt}\n\n## Response format\n\n{draft.expected_response_format}\n"
            private_tokens = result.ground_truth.anonymization_map.keys()
            if any(token in question for token in private_tokens):
                raise ValueError("question leaks a private identifier")
            artifacts.write_text("public", "question.md", question)
            artifacts.write_text("private", "answer.json", dump_json(result.answer))
            artifacts.write_text("private", "latent_truth.json", dump_json(result.ground_truth))
            artifacts.write_text("private", "scenario.json", dump_json(spec))
            if source.assets:
                source_manifest = SourceManifest(
                    source_kind=source.source_kind,
                    assets=[
                        SourceAssetRecord(
                            provider=asset.provider,
                            reference_id=asset.reference_id,
                            release=asset.release,
                            kind=asset.kind,
                            sha256=asset.sha256,
                            cached_path=str(asset.path),
                            metadata=asset.metadata,
                        )
                        for asset in source.assets
                    ],
                )
                artifacts.write_text("private", "source_manifest.json", dump_json(source_manifest))
            files = sorted(path for path in stage.rglob("*") if path.is_file())
            hashes = {str(path.relative_to(stage)): sha256(path) for path in files}
            manifest = GenerationManifest(
                case_id=case_id,
                status="complete",
                seed=spec.seed,
                backend=spec.execution.backend,
                tool_calls=runtime.calls,
                public_files=[f"public/{path}" for path in artifacts.paths("public")],
                file_sha256=hashes,
            )
            artifacts.write_text("private", "generation_manifest.json", dump_json(manifest))
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
