import httpx
import respx

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


def _make_article(i: int, title: str | None = ..., url: str | None = ...) -> dict:  # type: ignore
    """Create a test article. Use ... (Ellipsis) to use default, None to explicitly set None."""
    return {
        "title": title if title is not ... else f"Article {i}",
        "url": url if url is not ... else f"https://example.com/article-{i}",
        "publishedAt": "2026-05-08T12:00:00Z",
        "description": f"Description {i}",
    }


def _newsapi_response(articles: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok", "articles": articles})


async def test_newsapi_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    articles = [_make_article(i) for i in range(10)]

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response(articles))

        from news_agent.agents.newsapi import NewsAPIAgent

        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "newsapi"
    assert len(result.articles) == 10
    assert result.articles[0].source == "newsapi"
    assert result.articles[0].title == "Article 0"


async def test_newsapi_auto_skip_when_key_missing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    with respx.mock:
        from news_agent.agents.newsapi import NewsAPIAgent

        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error == "NEWSAPI_KEY not configured"
    assert result.articles == []
    assert not respx.calls  # no HTTP call was made


async def test_newsapi_filters_removed_articles(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    articles = [
        _make_article(0),
        _make_article(1, title="[Removed]"),
        _make_article(2, url="[Removed]"),
        _make_article(3, title=None),
        _make_article(4),
    ]

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response(articles))

        from news_agent.agents.newsapi import NewsAPIAgent

        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 2


async def test_newsapi_sends_api_key_header(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "my-secret-key")

    with respx.mock:
        route = respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response([]))

        from news_agent.agents.newsapi import NewsAPIAgent

        agent = NewsAPIAgent()
        await agent.fetch()

    assert route.called
    assert route.calls[0].request.headers.get("x-api-key") == "my-secret-key"


async def test_newsapi_api_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=httpx.Response(429))

        from news_agent.agents.newsapi import NewsAPIAgent

        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_newsapi_retries_on_transient_error(monkeypatch):
    """A 503 on the first attempt is retried and recovers on the second."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    articles = [_make_article(i) for i in range(10)]

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(side_effect=[httpx.Response(503), _newsapi_response(articles)])

        from news_agent.agents.newsapi import NewsAPIAgent

        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 10


async def test_newsapi_skips_articles_with_a_malformed_timestamp(monkeypatch):
    """A bad publishedAt must drop that item, not the whole page."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "key")
    from news_agent.agents.newsapi import NewsAPIAgent
    from news_agent.config import get_settings

    get_settings.cache_clear()

    broken = _make_article(2)
    broken["publishedAt"] = "not-a-date"

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response([_make_article(1), broken]))

        result = await NewsAPIAgent().fetch()

    assert result.error is None
    assert len(result.articles) == 1
