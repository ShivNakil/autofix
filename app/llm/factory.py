from langchain_core.language_models import BaseChatModel
from app.config import settings


def get_llm() -> BaseChatModel:
    provider = settings.llm_provider.lower().strip()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic.")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )

    if provider in {"gemini", "google"}:
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        "Use ollama, openai, anthropic, or gemini."
    )


class LLMServiceError(RuntimeError):
    """Normalized provider-facing error for the agent runtime."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


def classify_llm_error(exc: Exception) -> LLMServiceError:
    text = str(exc)
    lowered = text.lower()

    if "429" in lowered or "resourceexhausted" in lowered or "quota" in lowered:
        return LLMServiceError(
            "QUOTA_EXCEEDED",
            "LLM provider quota/rate limit was exceeded. "
            "Stop this run instead of repeatedly retrying.",
        )

    if "401" in lowered or "403" in lowered or "unauthorized" in lowered:
        return LLMServiceError(
            "AUTHENTICATION_ERROR",
            "LLM provider authentication or permission failed.",
        )

    if "timeout" in lowered:
        return LLMServiceError(
            "TIMEOUT",
            "LLM provider request timed out.",
        )

    return LLMServiceError(
        "PROVIDER_ERROR",
        f"LLM provider request failed: {text}",
    )
