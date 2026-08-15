"""Structured LLM clients and planning helpers."""

from __future__ import annotations

import json
from collections import deque
from typing import Protocol, TypeVar

from pydantic import BaseModel

from bio_mystery_synth.models import QuestionContext, QuestionDraft, ScenarioSpec, StrictModel
from bio_mystery_synth.runtime import capability_catalog

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def generate(self, schema: type[T], system: str, user: str) -> T: ...


class OpenAILLMClient:
    def __init__(self, model: str) -> None:
        if not model:
            raise ValueError("OpenAI model is required")
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model

    def generate(self, schema: type[T], system: str, user: str) -> T:
        response = self.client.responses.parse(
            model=self.model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            text_format=schema,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no parsed output")
        return response.output_parsed


class FakeLLMClient:
    def __init__(self, responses: list[BaseModel]) -> None:
        self.responses = deque(responses)

    def generate(self, schema: type[T], system: str, user: str) -> T:
        del system, user
        value = self.responses.popleft()
        return schema.model_validate(value.model_dump())


class ScenarioEnvelope(StrictModel):
    scenario: ScenarioSpec


class ScenarioPlanner:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def plan(self, request: str) -> ScenarioSpec:
        catalog = json.dumps(capability_catalog(), sort_keys=True)
        result = self.client.generate(
            ScenarioEnvelope,
            "Plan one closed-world bioinformatics case. Use only the supplied catalog and emit the requested schema.",
            f"Request:\n{request}\nCapability catalog:\n{catalog}",
        )
        return result.scenario


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
