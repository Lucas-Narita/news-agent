import re

import httpx
import pytest
import respx

from news_agent.agents.hackernews import HackerNewsAgent

HN_BASE = "https://hacker-news.firebaseio.com/v0"


def _make_item(i: int, has_url: bool = True) -> dict:
    return {
        "id": i,
        "title": f"Story {i}",
        "url": f"https://example.com/{i}" if has_url else None,
        "score": 100 + i,
        "time": 1700000000,
        "type": "story",
    }


async def test_hackernews_happy_path():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            return_value=httpx.Response(200, json=list(range(1, 21)))
        )
        respx.get(re.compile(rf"{re.escape(HN_BASE)}/item/\d+\.json")).mock(
            side_effect=lambda req: httpx.Response(
                200, json=_make_item(int(req.url.path.split("/")[-1].replace(".json", "")))
            )
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "hackernews"
    assert len(result.articles) == 10
    assert result.articles[0].source == "hackernews"
    assert result.articles[0].score == 101


async def test_hackernews_filters_items_without_url():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            return_value=httpx.Response(200, json=[1, 2, 3])
        )
        respx.get(re.compile(rf"{re.escape(HN_BASE)}/item/\d+\.json")).mock(
            side_effect=lambda req: httpx.Response(
                200,
                json=_make_item(
                    int(req.url.path.split("/")[-1].replace(".json", "")),
                    has_url=(int(req.url.path.split("/")[-1].replace(".json", "")) != 2),
                ),
            )
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 2


async def test_hackernews_network_timeout():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_hackernews_api_error():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            return_value=httpx.Response(500)
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []
