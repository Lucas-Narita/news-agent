from pathlib import Path

import pytest
from pydantic import ValidationError

from news_agent.config import Settings, get_settings
## test 2

def test_settings_requires_anthropic_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_reads_anthropic_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-test"


def test_optional_keys_default_to_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    s = Settings()
    assert s.newsapi_key is None
    assert s.github_token is None


def test_output_dir_defaults_to_output(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.output_dir == Path("output")


def test_output_dir_configurable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OUTPUT_DIR", "/tmp/digests")
    s = Settings()
    assert s.output_dir == Path("/tmp/digests")


def test_default_sources_includes_all_registered(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.default_sources == [
        "hackernews",
        "github",
        "newsapi",
        "reddit",
        "devto",
        "lobsters",
    ]


def test_request_timeout_defaults_to_10(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.request_timeout == 10.0


def test_request_timeout_configurable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("REQUEST_TIMEOUT", "3.5")
    s = Settings()
    assert s.request_timeout == 3.5


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
