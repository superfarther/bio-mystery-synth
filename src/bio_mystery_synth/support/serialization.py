import json
from typing import Any

from pydantic import BaseModel


def dump_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
