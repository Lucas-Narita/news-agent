import httpx
import respx

LOBSTERS_URL = "https://lobste.rs/hottest.json"


def _lobsters_story(i: int) -> dict:
    return {
        "title": f"Lobsters story {i}",
        "url": f"https://example.com/lobsters-{i}",
        "score": 20 + i,
        "created_at": "2026-05-01T12:00:00.000-07:00",
        "short_id": f"abc{i}",
    }


def _lobsters_response(n: int = 10) -> httpx.Response:
    return httpx.Response(200, json=[_lobsters_story(i) for i in range(n)])


async def test_lobsters_happy_path():
    with respx.mock:
        respx.get(LOBSTERS_URL).mock(return_value=_lobsters_response())

        from news_agent.agents.lobsters import LobstersAgent

        agent = LobstersAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "lobsters"
    assert len(result.articles) == 10
    assert result.articles[0].source == "lobsters"
    assert result.articles[0].score == 20


async def test_lobsters_skips_stories_without_url():
    story_with_url = _lobsters_story(0)
    story_without_url = _lobsters_story(1)
    story_without_url["url"] = ""  # Ask/Show posts have no external link

    with respx.mock:
        respx.get(LOBSTERS_URL).mock(
            return_value=httpx.Response(200, json=[story_with_url, story_without_url])
        )

        from news_agent.agents.lobsters import LobstersAgent

        agent = LobstersAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1


async def test_lobsters_skips_malformed_item():
    good = _lobsters_story(0)
    bad = _lobsters_story(1)
    del bad["title"]  # one malformed item must not sink the whole source

    with respx.mock:
        respx.get(LOBSTERS_URL).mock(return_value=httpx.Response(200, json=[good, bad]))

        from news_agent.agents.lobsters import LobstersAgent

        agent = LobstersAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1


async def test_lobsters_network_timeout():
    with respx.mock:
        respx.get(LOBSTERS_URL).mock(side_effect=httpx.TimeoutException("timeout"))

        from news_agent.agents.lobsters import LobstersAgent

        agent = LobstersAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_lobsters_api_error():
    with respx.mock:
        respx.get(LOBSTERS_URL).mock(return_value=httpx.Response(503))

        from news_agent.agents.lobsters import LobstersAgent

        agent = LobstersAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_lobsters_retries_on_transient_error():
    with respx.mock:
        respx.get(LOBSTERS_URL).mock(side_effect=[httpx.Response(503), _lobsters_response(3)])

        from news_agent.agents.lobsters import LobstersAgent

        agent = LobstersAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 3


async def test_lobsters_caps_results_at_limit():
    """Lobsters has no per_page parameter, so the cap must be applied client-side."""
    from news_agent.agents.lobsters import LIMIT, LobstersAgent

    with respx.mock:
        respx.get(LOBSTERS_URL).mock(return_value=_lobsters_response(LIMIT + 15))

        result = await LobstersAgent().fetch()

    assert len(result.articles) == LIMIT
