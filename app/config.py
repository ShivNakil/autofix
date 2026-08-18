from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:8b"

    ollama_base_url: str = "http://localhost:11434"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    max_iterations: int = 3
    test_timeout_seconds: int = 120
    workspace_dir: str = "workspace"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_dir).resolve()


settings = Settings()
