from dataclasses import dataclass
from typing import Any

from app.cache import Cache
from app.config import Settings
from app.llm.base import LLMProvider


@dataclass
class Deps:
    db: Any
    cache: Cache
    llm: LLMProvider
    graph: Any
    settings: Settings
    mongo_kind: str
    redis_kind: str
