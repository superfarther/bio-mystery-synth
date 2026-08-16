from bio_mystery_synth.core import AnswerSpec


def render_answer(answer: AnswerSpec) -> str:
    return "\n".join(
        f"{assertion.field}: {getattr(assertion, 'expected', '')}" for assertion in answer.assertions
    )
