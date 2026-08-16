from pathlib import Path

from pydantic import Field

from bio_mystery_synth.core.answer import AnswerSpec, GroundTruth
from bio_mystery_synth.core.base import StrictModel
from bio_mystery_synth.core.manifest import CaseIndexEntry
from bio_mystery_synth.core.question import QuestionContext


class FamilyResult(StrictModel):
    public_files: dict[str, str] = Field(default_factory=dict)
    ground_truth: GroundTruth
    answer: AnswerSpec
    question_context: QuestionContext


class GeneratedCase(StrictModel):
    case_id: str
    path: Path
    index: CaseIndexEntry
