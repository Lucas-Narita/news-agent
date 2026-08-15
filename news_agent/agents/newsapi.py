from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
LIMIT = 10


# NewsAPI blanks out withdrawn stories rather than omitting them.
REMOVED_MARKERS = (None, "[Removed]")


def _parse_article(item: dict, source: str) -> Article | None:
    """Build an Article from one NewsAPI item, or None if it is unusable."""
    if item.get("title") in REMOVED_MARKERS or item.get("url") in REMOVED_MARKERS:
        return None
    try:
        return Article(
            title=item["title"],
            url=item["url"],
            source=source,
            published_at=datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00")),
            summary=item.get("description"),
        )
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


class NewsAPIAgent(BaseAgent):
    name = "newsapi"

    def _precheck(self) -> str | None:
        if not get_settings().newsapi_key:
            return "NEWSAPI_KEY not configured"
        return None

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        settings = get_settings()

        async def _get():
            resp = await client.get(
                NEWSAPI_URL,
                params={"category": "technology", "language": "en", "pageSize": LIMIT},
                headers={"X-Api-Key": settings.newsapi_key},
            )
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        raw = resp.json().get("articles", [])

        return [article for item in raw if (article := _parse_article(item, self.name)) is not None]
