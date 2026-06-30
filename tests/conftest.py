import pytest

from news_agent.config import get_settings


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # ANTHROPIC_API_KEY is required in production, so make it present by default.
    # Tests that assert on its absence call monkeypatch.delenv() themselves.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
