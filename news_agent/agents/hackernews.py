import asyncio
import logging
from datetime import UTC, datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

logger = logging.getLogger(__name__)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
LIMIT = 10


def _parse_item(item: dict, source: str) -> Article | None:
    """Build an Article from one HN item, or None if the item is malformed.

    Matches the per-item guard the other agents already use: a story missing
    `title` or `time` used to raise and take the whole source down with it.
    """
    try:
        if not item.get("url"):
            return None
        return Article(
            title=item["title"],
            url=item["url"],
            source=source,
            score=item.get("score"),
            published_at=datetime.fromtimestamp(item["time"], tz=UTC),
        )
    except (KeyError, ValueError, TypeError, OSError):
        return None


class HackerNewsAgent(BaseAgent):
    name = "hackernews"

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        async def _get_top():
            resp = await client.get(f"{HN_BASE}/topstories.json")
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get_top)
        ids = resp.json()[:LIMIT]

        async def fetch_item(item_id: int) -> dict | None:
            try:
                r = await client.get(f"{HN_BASE}/item/{item_id}.json")
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                # One dead item must not sink the source, but silently dropping
                # it made a half-empty digest impossible to explain.
                logger.info("skipping HN item %s: %s", item_id, exc)
                return None

        items = await asyncio.gather(*[fetch_item(i) for i in ids])

        return [
            article
            for item in items
            if item and (article := _parse_item(item, self.name)) is not None
        ]
