from datetime import datetime
from unittest.mock import AsyncMock, patch

from news_agent.schemas.models import AgentResult, Article


def _ok_result(source: str, n: int = 3) -> AgentResult:
    articles = [
        Article(title=f"{source} story {i}", url=f"https://example.com/{source}/{i}", source=source)
        for i in range(n)
    ]
    return AgentResult(source=source, articles=articles, fetched_at=datetime.now())


def _err_result(source: str) -> AgentResult:
    return AgentResult(source=source, articles=[], fetched_at=datetime.now(), error="API failed")


async def test_run_digest_skips_unregistered_source_name(monkeypatch):
    """An unknown source name must be dropped without raising KeyError."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    from news_agent.orchestrator import run_digest

    settings = get_settings()

    with patch(
        "news_agent.orchestrator.generate_narrative",
        new=AsyncMock(return_value="# Digest"),
    ):
        result = await run_digest(["not-a-real-source"], settings)

    assert result.sources_used == []
    assert result.total_articles == 0


async def test_run_digest_survives_agent_raising_exception(monkeypatch):
    """If one agent's fetch() unexpectedly raises, the digest must still
    complete deterministically using the surviving sources."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch(
            "news_agent.agents.github.GitHubAgent.fetch",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch(
            "news_agent.orchestrator.generate_narrative",
            new=AsyncMock(return_value="# Digest"),
        ),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github"], settings)

    assert result.sources_used == ["hackernews"]
    assert result.total_articles == 2
    roster = {a.name: a for a in result.agents}
    assert roster["hackernews"].ok is True
    assert roster["github"].ok is False
    assert roster["github"].article_count == 0


async def test_run_digest_aggregates_all_sources(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch(
            "news_agent.agents.github.GitHubAgent.fetch",
            new=AsyncMock(return_value=_ok_result("github")),
        ),
        patch(
            "news_agent.agents.newsapi.NewsAPIAgent.fetch",
            new=AsyncMock(return_value=_ok_result("newsapi")),
        ),
        patch(
            "news_agent.orchestrator.generate_narrative",
            new=AsyncMock(return_value="# Digest"),
        ),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github", "newsapi"], settings)

    assert result.total_articles == 9
    assert set(result.sources_used) == {"hackernews", "github", "newsapi"}
    assert result.narrative == "# Digest"


async def test_run_digest_skips_failed_source(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch(
            "news_agent.agents.github.GitHubAgent.fetch",
            new=AsyncMock(return_value=_err_result("github")),
        ),
        patch(
            "news_agent.orchestrator.generate_narrative",
            new=AsyncMock(return_value="# Digest"),
        ),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github"], settings)

    assert "github" not in result.sources_used
    assert "hackernews" in result.sources_used
    assert result.total_articles == 3


async def test_run_digest_all_sources_fail_skips_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_llm = AsyncMock(return_value="# Digest")
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_err_result("hackernews")),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings)

    assert result.total_articles == 0
    assert result.sources_used == []
    assert "No articles available" in result.narrative
    mock_llm.assert_not_called()


async def test_run_digest_calls_generate_narrative_with_articles(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_llm = AsyncMock(return_value="# Digest")
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest

        await run_digest(["hackernews"], settings)

    mock_llm.assert_called_once()
    articles_arg = mock_llm.call_args.args[0]
    assert len(articles_arg) == 2


async def test_run_digest_llm_failure_falls_back_to_raw_list(monkeypatch):
    """If the LLM call fails but articles were fetched, degrade to the raw list."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    failing_llm = AsyncMock(side_effect=RuntimeError("API down"))
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=failing_llm),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings)

    assert result.total_articles == 2
    assert result.sources_used == ["hackernews"]
    assert "hackernews story 0" in result.narrative


async def test_run_digest_logs_exception_when_llm_fails(monkeypatch, caplog):
    """The LLM fallback must log the underlying error, not swallow it silently."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    failing_llm = AsyncMock(side_effect=RuntimeError("API down"))
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=failing_llm),
    ):
        from news_agent.orchestrator import run_digest

        with caplog.at_level("ERROR"):
            await run_digest(["hackernews"], settings)

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any(
        "narrative generation failed" in r.getMessage() and "API down" in str(r.exc_info)
        for r in errors
    )


async def test_run_digest_deduplicates_and_ranks_before_narrating(monkeypatch):
    """Cross-source duplicates collapse and the survivors reach the LLM ranked."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    shared_url = "https://example.com/shared"
    hn = AgentResult(
        source="hackernews",
        articles=[
            Article(title="hn copy", url=shared_url, source="hackernews", score=10),
            Article(title="hn unique", url="https://example.com/hn", source="hackernews", score=5),
        ],
        fetched_at=datetime.now(),
    )
    gh = AgentResult(
        source="github",
        articles=[Article(title="gh copy", url=shared_url, source="github", score=99)],
        fetched_at=datetime.now(),
    )

    mock_llm = AsyncMock(return_value="# Digest")
    with (
        patch("news_agent.agents.hackernews.HackerNewsAgent.fetch", new=AsyncMock(return_value=hn)),
        patch("news_agent.agents.github.GitHubAgent.fetch", new=AsyncMock(return_value=gh)),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github"], settings)

    # 3 fetched, but the shared URL collapses to 1 -> 2 unique articles
    assert result.total_articles == 2
    ranked = mock_llm.call_args.args[0]
    assert [a.score for a in ranked] == [99, 5]  # highest score first
    assert ranked[0].source == "github"  # the stronger copy of the shared URL won


async def test_run_digest_logs_warning_for_failed_source(monkeypatch, caplog):
    """A failed source degrades gracefully but is logged, not silently swallowed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch(
            "news_agent.agents.github.GitHubAgent.fetch",
            new=AsyncMock(return_value=_err_result("github")),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# Digest")),
    ):
        from news_agent.orchestrator import run_digest

        with caplog.at_level("WARNING"):
            await run_digest(["hackernews", "github"], settings)

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert any("github" in r.getMessage() and "API failed" in r.getMessage() for r in warnings)


async def test_run_digest_includes_ranked_articles_in_output(monkeypatch):
    """The digest carries the structured articles, not just the narrative text."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    fetched = _ok_result("hackernews", n=3)
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=fetched),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# Digest")),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings)

    assert len(result.articles) == 3
    assert result.articles[0].source == "hackernews"


async def test_run_digest_generated_at_is_timezone_aware(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings)

    assert result.generated_at.tzinfo is not None


async def test_run_digest_reports_agent_roster(monkeypatch):
    """agents[] carries one status per attempted source, ok reflecting success."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch(
            "news_agent.agents.github.GitHubAgent.fetch",
            new=AsyncMock(return_value=_err_result("github")),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github"], settings)

    roster = {a.name: a for a in result.agents}
    assert roster["hackernews"].ok is True
    assert roster["hackernews"].article_count == 2
    assert roster["github"].ok is False
    assert roster["github"].article_count == 0


async def test_run_digest_applies_limit_to_top_ranked(monkeypatch):
    """A limit keeps only the top-N ranked articles, trimming before the LLM."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    articles = [
        Article(title=f"s{i}", url=f"https://example.com/{i}", source="hackernews", score=i)
        for i in range(5)
    ]
    fetched = AgentResult(source="hackernews", articles=articles, fetched_at=datetime.now())

    mock_llm = AsyncMock(return_value="# Digest")
    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=fetched),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings, limit=2)

    assert result.total_articles == 2
    ranked = mock_llm.call_args.args[0]
    assert [a.score for a in ranked] == [4, 3]  # only the top 2 by score survive


async def test_run_digest_warns_about_unregistered_source_names(monkeypatch, caplog):
    """Dropping a name in silence made a thin digest look like a quiet day."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    from news_agent.orchestrator import run_digest

    settings = get_settings()

    with caplog.at_level("WARNING", logger="news_agent.orchestrator"):
        await run_digest(["not-a-real-source"], settings)

    assert "not-a-real-source" in caplog.text


async def test_run_digest_logs_a_pipeline_summary(monkeypatch, caplog):
    """--verbose should explain how many articles survived dedup."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    from news_agent.orchestrator import run_digest

    settings = get_settings()

    with (
        patch(
            "news_agent.agents.hackernews.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=3)),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
        caplog.at_level("INFO", logger="news_agent.orchestrator"),
    ):
        await run_digest(["hackernews"], settings)

    assert "left after dedup" in caplog.text
