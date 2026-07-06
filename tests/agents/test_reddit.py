import httpx
import respx

REDDIT_URL = "https://www.reddit.com/r/programming/hot.json"


def _reddit_child(i: int) -> dict:
    return {
        "data": {
            "title": f"Reddit post {i}",
            "url": f"https://example.com/reddit-{i}",
            "score": 100 + i,
            "created_utc": 1700000000,
            "permalink": f"/r/programming/comments/{i}/",
        }
    }


def _reddit_response(n: int = 10) -> httpx.Response:
    return httpx.Response(200, json={"data": {"children": [_reddit_child(i) for i in range(n)]}})


async def test_reddit_happy_path():
    with respx.mock:
        respx.get(REDDIT_URL).mock(return_value=_reddit_response())

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "reddit"
    assert len(result.articles) == 10
    assert result.articles[0].source == "reddit"
    assert result.articles[0].score == 100


async def test_reddit_sends_user_agent():
    with respx.mock:
        route = respx.get(REDDIT_URL).mock(return_value=_reddit_response(1))

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        await agent.fetch()

    assert route.called
    assert route.calls[0].request.headers.get("user-agent", "").startswith("news-agent")


async def test_reddit_skips_malformed_item():
    good = _reddit_child(0)
    bad = _reddit_child(1)
    del bad["data"]["title"]  # one malformed item must not sink the whole source

    with respx.mock:
        respx.get(REDDIT_URL).mock(
            return_value=httpx.Response(200, json={"data": {"children": [good, bad]}})
        )

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1


async def test_reddit_api_error():
    with respx.mock:
        respx.get(REDDIT_URL).mock(return_value=httpx.Response(503))

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_reddit_published_at_is_timezone_aware():
    with respx.mock:
        respx.get(REDDIT_URL).mock(return_value=_reddit_response(1))

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        result = await agent.fetch()

    assert result.articles[0].published_at.tzinfo is not None


async def test_reddit_retries_on_transient_error():
    with respx.mock:
        respx.get(REDDIT_URL).mock(side_effect=[httpx.Response(503), _reddit_response(3)])

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 3


async def test_reddit_skips_item_missing_url():
    """Items without a url field must be skipped, not sink the whole source."""
    good = _reddit_child(0)
    bad = _reddit_child(1)
    bad["data"]["url"] = None  # missing url

    with respx.mock:
        respx.get(REDDIT_URL).mock(
            return_value=httpx.Response(200, json={"data": {"children": [good, bad]}})
        )

        from news_agent.agents.reddit import RedditAgent

        agent = RedditAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1
