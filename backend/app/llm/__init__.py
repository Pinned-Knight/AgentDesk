from app.config import Settings
from app.llm.base import Classification, LLMProvider, ResponseContext
from app.llm.mock import MockLLM
from app.llm.openai_compat import OpenAICompatLLM


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai_compat":
        return OpenAICompatLLM(settings.llm_base_url, settings.llm_api_key, settings.llm_model,
                               settings.llm_timeout_s)
    return MockLLM(token_delay_s=settings.mock_token_delay_ms / 1000)


__all__ = ["Classification", "LLMProvider", "MockLLM", "OpenAICompatLLM", "ResponseContext", "build_llm"]
