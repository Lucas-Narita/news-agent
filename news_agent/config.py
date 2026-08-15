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
    # gt=0 turns a typo like REQUEST_TIMEOUT=0 into a startup error instead of
    # httpx treating it as "fail immediately" on every source.
    request_timeout: float = Field(default=10.0, gt=0)
    # Default freshness window for --cache. Lives here rather than as a CLI
    # literal so scheduled runs can widen it without changing the invocation.
    cache_ttl: int = Field(default=3600, gt=0)
    # Model and budget are the two knobs most likely to be tuned per
    # deployment (cost vs. depth), so they belong in config rather than as
    # module constants that require a code change to move.
    anthropic_model: str = "claude-sonnet-4-6"
    max_tokens: int = Field(default=1024, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
