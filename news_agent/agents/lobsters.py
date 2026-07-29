from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

LOBSTERS_URL = "https://lobste.rs/hottest.json"


def _parse_story(story: dict, source: str) -> Article | None:
    """Build an Article from one Lobsters story, or None if the item is malformed."""
    try:
        if not story.get("url"):
            return None
        return Article(
            title=story["title"],
            url=story["url"],
            source=source,
            score=story.get("score"),
            published_at=datetime.fromisoformat(story["created_at"]),
        )
    except (KeyError, ValueError, TypeError):
        return None


class LobstersAgent(BaseAgent):
    name = "lobsters"

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        async def _get():
            resp = await client.get(LOBSTERS_URL)
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        stories = resp.json()

        return [
            article for story in stories if (article := _parse_story(story, self.name)) is not None
        ]
