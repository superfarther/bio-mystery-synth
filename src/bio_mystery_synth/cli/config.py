from pathlib import Path
from typing import Literal

from pydantic import Field

from bio_mystery_synth.core import Backend, Difficulty, StrictModel


class BatchJob(StrictModel):
    family: str
    difficulty: Difficulty = Difficulty.MEDIUM
    count: int = Field(default=1, ge=1)
    seed: int = Field(default=0, ge=0)
    backend: Backend = Backend.LOCAL
    local_device: str = "cuda"


class LLMSettings(StrictModel):
    provider: Literal["none", "openai"] = "none"
    model: str | None = None


class BatchConfig(StrictModel):
    output_root: Path = Path(".")
    max_workers: int = Field(default=1, ge=1)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    jobs: list[BatchJob]
