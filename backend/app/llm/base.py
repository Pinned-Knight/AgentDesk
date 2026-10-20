from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol

INTENTS = ("order_status", "return_refund", "faq", "human_handoff", "smalltalk", "unknown")


@dataclass
class Classification:
    intent: str
    confidence: float
    entities: dict[str, str] = field(default_factory=dict)


@dataclass
class ResponseContext:
    """Everything the responder is allowed to ground its answer in."""

    message: str
    history: list[dict[str, str]]
    intent: str
    entities: dict[str, Any]
    tool_results: list[dict[str, Any]]
    kb: list[dict[str, Any]]
    escalated: bool = False
    ticket_id: str | None = None


class LLMProvider(Protocol):
    name: str

    async def classify(self, message: str, history: list[dict[str, str]]) -> Classification: ...

    def respond(self, ctx: ResponseContext) -> AsyncIterator[str]: ...
