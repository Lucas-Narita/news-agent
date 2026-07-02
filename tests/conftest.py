from unittest.mock import AsyncMock

import pytest

from news_agent.config import get_settings


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # ANTHROPIC_API_KEY is required in production, so make it present by default.
    # Tests that assert on its absence call monkeypatch.delenv() themselves.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # Pin the provider to the anthropic default: a host shell exporting
    # LLM_PROVIDER=github would otherwise leak into every test.
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Neutralize retry backoff so tests never actually sleep.

    Tests in test_retry.py that assert on the backoff delays override this with
    their own mock.
    """
    monkeypatch.setattr("news_agent.retry.sleep", AsyncMock())
