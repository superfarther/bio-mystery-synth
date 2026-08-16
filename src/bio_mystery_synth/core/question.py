from bio_mystery_synth.core.base import StrictModel


class QuestionContext(StrictModel):
    task_family: str
    goal: str
    public_files: list[str]
    answer_format: str
    default_question: str


class QuestionDraft(StrictModel):
    title: str
    prompt: str
    expected_response_format: str
    referenced_files: list[str]
