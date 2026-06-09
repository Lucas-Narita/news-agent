from unittest.mock import AsyncMock, MagicMock, patch

from news_agent.schemas.models import Article


def _make_article(source: str = "hackernews") -> Article:
    return Article(title="Test Story", url="https://example.com", source=source)


def _mock_response(text: str = "# Digest\nTop stories.") -> MagicMock:
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
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
