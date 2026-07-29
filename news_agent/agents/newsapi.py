from datetime import datetime, timezone

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
LIMIT = 10


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

        return [
            Article(
                title=a["title"],
                url=a["url"],
                source=self.name,
                published_at=datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00")),
                summary=a.get("description"),
            )
            for a in raw
            if a.get("title") not in (None, "[Removed]") and a.get("url") not in (None, "[Removed]")
        ]
