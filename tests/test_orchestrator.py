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


async def test_run_digest_aggregates_all_sources(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    with (
        patch(
            "news_agent.orchestrator.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch(
            "news_agent.orchestrator.GitHubAgent.fetch",
            new=AsyncMock(return_value=_ok_result("github")),
        ),
        patch(
            "news_agent.orchestrator.NewsAPIAgent.fetch",
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
            "news_agent.orchestrator.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch(
            "news_agent.orchestrator.GitHubAgent.fetch",
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
            "news_agent.orchestrator.HackerNewsAgent.fetch",
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
            "news_agent.orchestrator.HackerNewsAgent.fetch",
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
            "news_agent.orchestrator.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=failing_llm),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings)

    assert result.total_articles == 2
    assert result.sources_used == ["hackernews"]
    assert "hackernews story 0" in result.narrative


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
        patch("news_agent.orchestrator.HackerNewsAgent.fetch", new=AsyncMock(return_value=hn)),
        patch("news_agent.orchestrator.GitHubAgent.fetch", new=AsyncMock(return_value=gh)),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github"], settings)

    # 3 fetched, but the shared URL collapses to 1 -> 2 unique articles
    assert result.total_articles == 2
    ranked = mock_llm.call_args.args[0]
    assert [a.score for a in ranked] == [99, 5]  # highest score first
    assert ranked[0].source == "github"  # the stronger copy of the shared URL won
