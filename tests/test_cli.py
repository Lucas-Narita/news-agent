from datetime import datetime
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from news_agent.schemas.models import DigestOutput

runner = CliRunner()


def _mock_digest() -> DigestOutput:
    return DigestOutput(
        narrative="Top stories this hour.",
        sources_used=["hackernews"],
        total_articles=3,
        generated_at=datetime.now(),
    )


def test_config_check_all_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1234")
    monkeypatch.setenv("NEWSAPI_KEY", "news-test-5678")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test-9012")
    from news_agent.cli import app

    result = runner.invoke(app, ["config", "check"])
    assert result.exit_code == 0
    assert "ANTHROPIC_API_KEY" in result.output
    assert "OK" in result.output


def test_config_check_optional_missing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1234")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from news_agent.cli import app

    result = runner.invoke(app, ["config", "check"])
    assert result.exit_code == 0
    assert "OPTIONAL" in result.output


def test_config_check_missing_required(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from news_agent.cli import app

    result = runner.invoke(app, ["config", "check"])
    assert result.exit_code == 1


def test_resolve_sources_from_flag(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import resolve_sources
    from news_agent.config import get_settings

    settings = get_settings()
    assert resolve_sources("hackernews,github", settings) == ["hackernews", "github"]


def test_resolve_sources_auto_detects_missing_newsapi(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import resolve_sources
    from news_agent.config import get_settings

    settings = get_settings()
    result = resolve_sources(None, settings)
    assert "newsapi" not in result
    assert "hackernews" in result
    assert "github" in result


def test_resolve_sources_includes_newsapi_when_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key")
    from news_agent.cli import resolve_sources
    from news_agent.config import get_settings

    settings = get_settings()
    result = resolve_sources(None, settings)
    assert "newsapi" in result


def test_run_no_file_prints_narrative(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app

    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])
    assert result.exit_code == 0
    assert "Top stories this hour." in result.output


def test_run_writes_md_file_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app

    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(app, ["run", "--sources", "hackernews"])
    assert result.exit_code == 0
    md_files = list(tmp_path.glob("digest-*.md"))
    assert len(md_files) == 1
    assert "Top stories this hour." in md_files[0].read_text()


def test_version_flag_shows_version():
    from importlib.metadata import version

    from news_agent.cli import app

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "news-agent" in result.output
    assert version("news-agent") in result.output
