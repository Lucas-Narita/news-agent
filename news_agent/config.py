from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: Literal["anthropic", "github"] = "anthropic"
    anthropic_api_key: str | None = None
    newsapi_key: str | None = None
    github_token: str | None = None
    output_dir: Path = Path("output")
    default_sources: list[str] = [
        "hackernews",
        "github",
        "newsapi",
        "reddit",
        "devto",
        "lobsters",
    ]
    request_timeout: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def require_credential_for_provider(self) -> "Settings":
        """Fail fast at startup instead of at narrative time."""
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic (the default). "
                "Set the key or switch to LLM_PROVIDER=github."
            )
        if self.llm_provider == "github" and not self.github_token:
            raise ValueError(
                "GITHUB_TOKEN is required when LLM_PROVIDER=github. "
                "Set a token (in GitHub Actions, grant `models: read` and pass the "
                "built-in GITHUB_TOKEN)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
