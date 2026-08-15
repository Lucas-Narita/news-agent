from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

LOBSTERS_URL = "https://lobste.rs/hottest.json"
# Lobsters has no per_page parameter, so the cap is applied client-side. Every
# other agent tops out at 10; leaving this one unbounded let a single source
# return 25 stories and dominate the ranked list.
LIMIT = 10


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
        """Fetch the hottest Lobsters stories and parse them into articles.

        Malformed stories are skipped individually via ``_parse_story``; only
        a network/HTTP failure propagates to fetch().
        """

        async def _get():
            resp = await client.get(LOBSTERS_URL)
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        stories = resp.json()[:LIMIT]

        return [
            article for story in stories if (article := _parse_story(story, self.name)) is not None
        ]
