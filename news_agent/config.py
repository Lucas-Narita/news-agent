from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    newsapi_key: str | None = None
    github_token: str | None = None
    output_dir: Path = Path("output")
    default_sources: list[str] = ["hackernews", "github", "newsapi"]
    request_timeout: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
