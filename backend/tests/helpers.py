import json
import uuid

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_settings(**overrides) -> Settings:
    """Isolated settings per test. If MONGODB_URI / REDIS_URL are exported (CI integration job),
    the very same suite runs against real MongoDB and Redis — each test gets its own DB and key prefix."""
    base = dict(
        mongodb_db=f"agentdesk_test_{uuid.uuid4().hex[:8]}",
        redis_prefix=f"t{uuid.uuid4().hex[:8]}",
        llm_provider="mock",
        mock_token_delay_ms=0,
        rate_limit_per_min=10_000,
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


def new_client(**overrides) -> TestClient:
    return TestClient(create_app(make_settings(**overrides)))


def new_sid() -> str:
    return uuid.uuid4().hex


def chat(client: TestClient, message: str, sid: str | None = None):
    return client.post("/api/chat", json={"session_id": sid or new_sid(), "message": message})


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        name, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if name:
            events.append((name, data))
    return events
