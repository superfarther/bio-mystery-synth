from pathlib import Path

from bio_mystery_synth.core import AnswerSpec, GenerationManifest, GroundTruth, SourceManifest
from bio_mystery_synth.support import sha256
from bio_mystery_synth.task_families.registry import FamilyRegistry, builtin_family_registry


def validate_case(case_path: Path, families: FamilyRegistry | None = None) -> list[str]:
    families = families or builtin_family_registry()
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
        scenario = families.validate_scenario_json((private / "scenario.json").read_text())
        manifest = GenerationManifest.model_validate_json((private / "generation_manifest.json").read_text())
        families.get(scenario.task_family)
        if scenario.source_kind == "external-reference":
            SourceManifest.model_validate_json((private / "source_manifest.json").read_text())
    except Exception as exc:
        return [f"invalid private model: {exc}"]
    if answer.oracle_type != truth.oracle_type:
        errors.append("answer and truth oracle types differ")
    public_paths = [path for path in public.rglob("*") if path.is_file()]
    public_text = "\n".join(path.read_text(errors="ignore") for path in public_paths)
    public_names = "\n".join(str(path.relative_to(public)) for path in public_paths)
    for raw_id in truth.anonymization_map:
        if raw_id in public_text or raw_id in public_names:
            errors.append(f"public data leaks {raw_id}")
    for relative, expected in manifest.file_sha256.items():
        path = case_path / relative
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"hash mismatch: {relative}")
    actual_public = sorted(f"public/{path.relative_to(public)}" for path in public_paths)
    if actual_public != sorted(manifest.public_files):
        errors.append("manifest public inventory differs")
    return errors
