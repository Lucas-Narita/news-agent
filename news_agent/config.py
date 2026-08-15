from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_sources() -> list[str]:
    """Every registered source name, resolved lazily.

    The import lives inside the function because ``registry`` imports the
    agents, which import ``Settings`` from this module — a cycle at import
    time. A Settings instance is only ever built at runtime, by which point
    every module is loaded, so the lazy import is safe and removes the
    hand-maintained copy of the source list that could drift.
    """
    from news_agent.agents.registry import SOURCE_NAMES

    return list(SOURCE_NAMES)


class Settings(BaseSettings):
    anthropic_api_key: str
    newsapi_key: str | None = None
    github_token: str | None = None
    output_dir: Path = Path("output")
    default_sources: list[str] = Field(default_factory=_default_sources)
    request_timeout: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
