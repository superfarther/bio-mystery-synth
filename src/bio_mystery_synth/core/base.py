from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Backend(StrEnum):
    LOCAL = "local"
    MODAL = "modal"


class OracleType(StrEnum):
    INJECTED = "injected_truth"
    DETERMINISTIC = "deterministic_computation"
    MODEL_DEFINED = "model_defined"
