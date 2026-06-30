import httpx
import respx

DEVTO_URL = "https://dev.to/api/articles"


def _devto_article(i: int) -> dict:
    return {
        "title": f"Dev.to article {i}",
        "url": f"https://dev.to/user/article-{i}",
        "positive_reactions_count": 50 + i,
        "published_at": "2026-05-01T12:00:00Z",
        "description": f"Summary {i}",
    }


def _devto_response(n: int = 10) -> httpx.Response:
    return httpx.Response(200, json=[_devto_article(i) for i in range(n)])


async def test_devto_happy_path():
    with respx.mock:
        respx.get(DEVTO_URL).mock(return_value=_devto_response())

        from news_agent.agents.devto import DevToAgent

        agent = DevToAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "devto"
    assert len(result.articles) == 10
    assert result.articles[0].source == "devto"
    assert result.articles[0].score == 50
    assert result.articles[0].summary == "Summary 0"


async def test_devto_api_error():
    with respx.mock:
        respx.get(DEVTO_URL).mock(return_value=httpx.Response(503))

        from news_agent.agents.devto import DevToAgent

        agent = DevToAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_devto_retries_on_transient_error():
    with respx.mock:
        respx.get(DEVTO_URL).mock(side_effect=[httpx.Response(503), _devto_response(3)])

        from news_agent.agents.devto import DevToAgent

        agent = DevToAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 3
