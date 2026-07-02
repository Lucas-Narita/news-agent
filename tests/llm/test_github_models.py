import json

import httpx
import pytest
import respx

from news_agent.schemas.models import Article

GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"


def _make_article(source: str = "hackernews") -> Article:
    return Article(title="Test Story", url="https://example.com", source=source)


def _chat_response(text: str = "# Digest\nTop stories.") -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


async def test_generate_narrative_github_returns_text(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    from news_agent.config import get_settings

    settings = get_settings()

    with respx.mock:
        route = respx.post(GITHUB_MODELS_URL).mock(return_value=_chat_response())
        from news_agent.llm.github_models import generate_narrative_github

        result = await generate_narrative_github([_make_article()], settings)

    assert result == "# Digest\nTop stories."
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer ghs_test"
    body = json.loads(request.content)
    assert body["model"] == "openai/gpt-4o-mini"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"
    assert "Test Story" in body["messages"][1]["content"]


async def test_generate_narrative_github_requires_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from news_agent.config import get_settings

    settings = get_settings()
    from news_agent.llm.github_models import generate_narrative_github

    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        await generate_narrative_github([_make_article()], settings)


async def test_generate_narrative_github_handles_empty_content(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    from news_agent.config import get_settings

    settings = get_settings()

    with respx.mock:
        respx.post(GITHUB_MODELS_URL).mock(return_value=_chat_response(""))
        from news_agent.llm.github_models import generate_narrative_github

        result = await generate_narrative_github([_make_article()], settings)

    assert result == "Narrative unavailable — the model returned no text content."


async def test_generate_narrative_github_retries_on_server_error(monkeypatch):
    """A transient 5xx must not sink the daily digest — retry like every other source."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    from news_agent.config import get_settings

    settings = get_settings()

    with respx.mock:
        route = respx.post(GITHUB_MODELS_URL).mock(
            side_effect=[
                httpx.Response(500, json={"message": "boom"}),
                _chat_response("# Digest after retry"),
            ]
        )
        from news_agent.llm.github_models import generate_narrative_github

        result = await generate_narrative_github([_make_article()], settings)

    assert result == "# Digest after retry"
    assert route.call_count == 2


async def test_generate_narrative_github_warns_on_truncated_output(monkeypatch, caplog):
    """finish_reason=length means the digest was cut mid-sentence — log it loudly."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    from news_agent.config import get_settings

    settings = get_settings()

    truncated = httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "# Digest cut off mid"}, "finish_reason": "length"}]
        },
    )
    with respx.mock:
        respx.post(GITHUB_MODELS_URL).mock(return_value=truncated)
        from news_agent.llm.github_models import generate_narrative_github

        with caplog.at_level("WARNING"):
            result = await generate_narrative_github([_make_article()], settings)

    assert result == "# Digest cut off mid"
    assert any("truncated" in r.getMessage() for r in caplog.records)


async def test_generate_narrative_github_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    from news_agent.config import get_settings

    settings = get_settings()

    with respx.mock:
        respx.post(GITHUB_MODELS_URL).mock(
            return_value=httpx.Response(429, json={"message": "rate limited"})
        )
        from news_agent.llm.github_models import generate_narrative_github

        with pytest.raises(httpx.HTTPStatusError):
            await generate_narrative_github([_make_article()], settings)
