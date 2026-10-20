from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = {}
    result: dict[str, Any] = {}


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    confidence: float
    tools: list[ToolCall] = []
    escalated: bool = False
    ticket_id: str | None = None
    latency_ms: float
    cached: bool = False
    guardrail: str | None = None


class ConversationSummary(BaseModel):
    session_id: str
    started_at: str
    last_message_at: str
    turns: int
    last_intent: str | None = None
    escalated: bool = False


class StoredMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    intent: str | None = None
    tools: list[ToolCall] = []
    escalated: bool = False
    latency_ms: float | None = None
    created_at: str


class ConversationDetail(BaseModel):
    session_id: str
    messages: list[StoredMessage]


class IntentCount(BaseModel):
    intent: str
    count: int


class ToolCount(BaseModel):
    name: str
    count: int


class DailyCount(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    total_conversations: int
    total_messages: int
    escalation_rate: float
    avg_latency_ms: float
    cache_hit_rate: float
    intents: list[IntentCount]
    tools: list[ToolCount]
    daily: list[DailyCount]


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str
    llm_provider: str
    mongo: str
    redis: str
