from bio_mystery_synth.authoring.clients import LLMClient
from bio_mystery_synth.core import QuestionContext, QuestionDraft


class QuestionWriter:
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client

    def write(self, context: QuestionContext) -> QuestionDraft:
        if self.client is None:
            return QuestionDraft(
                title=context.goal,
                prompt=context.default_question,
                expected_response_format=context.answer_format,
                referenced_files=context.public_files,
            )
        return self.client.generate(
            QuestionDraft,
            (
                "Write a self-contained bioinformatics question. Do not invent files, answers, accessions, organisms, "
                "or hidden facts. Preserve the requested response format."
            ),
            context.model_dump_json(indent=2),
        )
