from __future__ import annotations

from collections import deque
from typing import Protocol, TypeVar

from pydantic import BaseModel

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
