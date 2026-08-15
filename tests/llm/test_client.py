from unittest.mock import AsyncMock, MagicMock, patch

from news_agent.schemas.models import Article


def _make_article(source: str = "hackernews") -> Article:
    return Article(title="Test Story", url="https://example.com", source=source)


def _mock_response(
    text: str = "# Digest\nTop stories.", stop_reason: str = "end_turn"
) -> MagicMock:
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = stop_reason
    return response


async def test_generate_narrative_returns_text(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response("# Digest\nTop stories."))
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        result = await generate_narrative([_make_article()], settings)

    assert result == "# Digest\nTop stories."


async def test_generate_narrative_uses_cache_control(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response())
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        await generate_narrative([_make_article()], settings)

    call_kwargs = mock_create.call_args.kwargs
    system = call_kwargs["system"]
    assert any(block.get("cache_control") == {"type": "ephemeral"} for block in system)


async def test_generate_narrative_uses_correct_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response())
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        await generate_narrative([_make_article()], settings)

    assert mock_create.call_args.kwargs["model"] == "claude-sonnet-4-6"


async def test_generate_narrative_passes_date_and_sources(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response())
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        await generate_narrative([_make_article("hackernews"), _make_article("github")], settings)

    user_content = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "hackernews" in user_content
    assert "github" in user_content
    assert "Date:" in user_content


async def test_generate_narrative_handles_empty_content(monkeypatch):
    """A refusal / empty response must degrade to a string, never IndexError."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    empty = MagicMock()
    empty.content = []
    mock_create = AsyncMock(return_value=empty)
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        result = await generate_narrative([_make_article()], settings)

    assert isinstance(result, str)
    assert result


async def test_generate_narrative_warns_on_truncation(monkeypatch, caplog):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response(stop_reason="max_tokens"))
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        with caplog.at_level("WARNING", logger="news_agent.llm.client"):
            await generate_narrative([_make_article()], settings)

    assert any("truncated" in record.message for record in caplog.records)


async def test_generate_narrative_uses_configured_model_and_budget(monkeypatch):
    """Model and token budget are deployment knobs, not module constants."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("MAX_TOKENS", "256")
    from news_agent.config import Settings

    settings = Settings()

    mock_create = AsyncMock(return_value=_mock_response())
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative

        await generate_narrative([_make_article()], settings)

    kwargs = mock_create.await_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"
    assert kwargs["max_tokens"] == 256


async def test_generate_narrative_joins_multiple_text_blocks(monkeypatch):
    """Taking only the first block silently truncated multi-block responses."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import Settings

    def _block(text: str) -> MagicMock:
        block = MagicMock()
        block.type = "text"
        block.text = text
        return block

    response = MagicMock()
    response.content = [_block("# Digest"), _block("## Trends")]
    response.stop_reason = "end_turn"

    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = AsyncMock(return_value=response)
        from news_agent.llm.client import generate_narrative

        result = await generate_narrative([_make_article()], Settings())

    assert result == "# Digest\n## Trends"
