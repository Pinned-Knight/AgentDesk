from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Infrastructure — leave unset to run fully in-memory ("demo mode").
    mongodb_uri: str | None = None
    mongodb_db: str = "agentdesk"
    redis_url: str | None = None
    redis_prefix: str = "agentdesk"

    # LLM — "mock" is a deterministic offline provider; "openai_compat" talks to any
    # OpenAI-compatible /chat/completions endpoint (OpenAI, Gemini, Groq, Ollama, ...).
    llm_provider: Literal["mock", "openai_compat"] = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_s: float = 30.0
    mock_token_delay_ms: int = 12

    # Behaviour
    rate_limit_per_min: int = 30
    memory_turns: int = 8
    cache_ttl_s: int = 300
    seed_demo_data: bool = True
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def mode(self) -> str:
        return "demo" if self.llm_provider == "mock" else "live"


@lru_cache
def get_settings() -> Settings:
    return Settings()
