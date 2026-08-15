from bio_mystery_synth.llm import FakeLLMClient, QuestionWriter
from bio_mystery_synth.models import QuestionContext, QuestionDraft


def test_question_writer_uses_structured_client() -> None:
    draft = QuestionDraft(
        title="Title",
        prompt="Prompt",
        expected_response_format="Format",
        referenced_files=["data/input.fasta"],
    )
    context = QuestionContext(
        task_family="example",
        goal="Goal",
        public_files=["data/input.fasta"],
        answer_format="Format",
        default_question="Default",
    )
    assert QuestionWriter(FakeLLMClient([draft])).write(context) == draft
