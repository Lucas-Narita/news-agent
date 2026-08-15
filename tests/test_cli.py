import json
import logging
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


def test_run_with_cache_skips_second_fetch(monkeypatch):
    from news_agent.cli import app

    mock_run_digest = AsyncMock(return_value=_mock_digest())
    with patch("news_agent.cli.run_digest", new=mock_run_digest):
        first = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews", "--cache"])
        second = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews", "--cache"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert mock_run_digest.await_count == 1
    assert "Using cached digest" in second.output


def test_run_without_cache_flag_always_fetches(monkeypatch):
    from news_agent.cli import app

    mock_run_digest = AsyncMock(return_value=_mock_digest())
    with patch("news_agent.cli.run_digest", new=mock_run_digest):
        runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])
        runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])

    assert mock_run_digest.await_count == 2


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


def test_resolve_sources_default_includes_all_seven_agents(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key")
    from news_agent.cli import resolve_sources
    from news_agent.config import get_settings

    settings = get_settings()
    result = resolve_sources(None, settings)
    assert set(result) == {
        "hackernews",
        "github",
        "newsapi",
        "reddit",
        "devto",
        "lobsters",
        "arxiv",
    }


def test_resolve_sources_drops_unknown_names(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.cli import resolve_sources
    from news_agent.config import get_settings

    settings = get_settings()
    result = resolve_sources("hackernews,not-a-real-source", settings)
    assert result == ["hackernews"]


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


def test_run_forwards_limit_to_orchestrator(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app

    mock = AsyncMock(return_value=_mock_digest())
    with patch("news_agent.cli.run_digest", new=mock):
        result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews", "--limit", "5"])
    assert result.exit_code == 0
    assert mock.call_args.kwargs["limit"] == 5


def test_run_verbose_configures_logging(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app

    with (
        patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())),
        patch("news_agent.cli.configure_logging") as mock_cfg,
    ):
        result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews", "--verbose"])
    assert result.exit_code == 0
    mock_cfg.assert_called_once_with(verbose=True)


def test_run_format_json_outputs_pure_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app

    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(
            app, ["run", "--no-file", "--sources", "hackernews", "--format", "json"]
        )
    assert result.exit_code == 0
    data = json.loads(result.stdout)  # stdout must be pure JSON, no progress noise
    assert data["narrative"] == "Top stories this hour."
    assert data["total_articles"] == 3


def test_run_json_stdout_pure_when_source_fails(monkeypatch):
    """A failed source logs a WARNING; it must NOT leak into the JSON on stdout."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    logging.getLogger("news_agent").handlers.clear()  # force the stderr handler to attach

    from news_agent.cli import app
    from news_agent.schemas.models import AgentResult, Article

    ok = AgentResult(
        source="hackernews",
        articles=[Article(title="t", url="https://example.com/a", source="hackernews")],
        fetched_at=datetime.now(),
    )
    err = AgentResult(source="github", articles=[], fetched_at=datetime.now(), error="boom")

    isolated = CliRunner()
    with (
        patch("news_agent.agents.hackernews.HackerNewsAgent.fetch", new=AsyncMock(return_value=ok)),
        patch("news_agent.agents.github.GitHubAgent.fetch", new=AsyncMock(return_value=err)),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
    ):
        result = isolated.invoke(
            app, ["run", "--no-file", "--sources", "hackernews,github", "--format", "json"]
        )

    assert result.exit_code == 0
    json.loads(result.stdout)  # raises if the WARNING leaked into stdout


def test_version_flag_shows_version():
    from importlib.metadata import version

    from news_agent.cli import app

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "news-agent" in result.output
    assert version("news-agent") in result.output


def test_run_config_validation_error(monkeypatch):
    """When ANTHROPIC_API_KEY is missing, run command exits with code 1."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from news_agent.cli import app
    from news_agent.config import get_settings

    get_settings.cache_clear()
    result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])
    get_settings.cache_clear()
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output
    assert ".env.example" in result.output


def test_run_no_active_sources(monkeypatch):
    """When only unavailable sources are requested, exit with code 1."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app
    from news_agent.config import get_settings

    get_settings.cache_clear()
    result = runner.invoke(app, ["run", "--no-file", "--sources", "newsapi"])
    get_settings.cache_clear()
    assert result.exit_code == 1
    assert "No sources available" in result.output


def test_run_digest_exception(monkeypatch):
    """When run_digest raises an exception, exit with code 1."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app

    with patch("news_agent.cli.run_digest", side_effect=RuntimeError("Test error")):
        result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_run_warns_about_unknown_source_names(monkeypatch):
    """A typo in --sources must be reported, not silently dropped."""
    from news_agent.cli import app

    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(
            app, ["run", "--no-file", "--sources", "hackernwes,hackernews"]
        )

    assert result.exit_code == 0
    assert "Unknown source(s) ignored: hackernwes" in result.output


def test_run_does_not_warn_for_valid_sources(monkeypatch):
    from news_agent.cli import app

    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])

    assert "Unknown source" not in result.output


def test_run_rejects_non_positive_limit():
    """--limit 0 silently produced an empty digest; it should be a usage error."""
    from news_agent.cli import app

    result = runner.invoke(app, ["run", "--no-file", "--limit", "0"])

    assert result.exit_code != 0


def test_output_filename_follows_the_digest_timestamp(tmp_path, monkeypatch):
    """The file name must match the timestamp stamped inside the digest."""
    from datetime import timezone

    from news_agent.cli import app

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    from news_agent.config import get_settings

    get_settings.cache_clear()

    digest = _mock_digest()
    digest.generated_at = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)

    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=digest)):
        result = runner.invoke(app, ["run", "--sources", "hackernews"])

    get_settings.cache_clear()
    assert result.exit_code == 0
    assert (tmp_path / "digest-2026-01-02-03.md").exists()
