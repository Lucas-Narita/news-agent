from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    newsapi_key: str | None = None
    github_token: str | None = None
    output_dir: Path = Path("output")
    # Kept as a literal (not imported from news_agent.agents.registry) to avoid a
    # circular import: agents already import Settings from this module. Must stay
    # in sync with news_agent.agents.registry.SOURCE_NAMES.
    default_sources: list[str] = [
        "hackernews",
        "github",
        "newsapi",
        "reddit",
        "devto",
        "lobsters",
        "arxiv",
    ]
    request_timeout: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
