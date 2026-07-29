from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

DEVTO_URL = "https://dev.to/api/articles"
LIMIT = 10
TOP_DAYS = 7


def _parse_article(item: dict, source: str) -> Article | None:
    """Build an Article from one Dev.to item, or None if the item is malformed."""
    try:
        if not item.get("url"):
            return None
        return Article(
            title=item["title"],
            url=item["url"],
            source=source,
            score=item.get("positive_reactions_count"),
            summary=item.get("description"),
            published_at=datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")),
        )
    except (KeyError, ValueError, TypeError):
        return None


class DevToAgent(BaseAgent):
    name = "devto"

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        """Fetch the top Dev.to articles of the last TOP_DAYS days.

        Malformed items are skipped individually via ``_parse_article``; only
        a network/HTTP failure propagates to fetch().
        """

        async def _get():
            resp = await client.get(DEVTO_URL, params={"per_page": LIMIT, "top": TOP_DAYS})
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        raw = resp.json()

        return [article for item in raw if (article := _parse_article(item, self.name)) is not None]
