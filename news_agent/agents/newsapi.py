from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.schemas.models import AgentResult, Article

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
LIMIT = 10


class NewsAPIAgent(BaseAgent):
    name = "newsapi"

    async def fetch(self) -> AgentResult:
        settings = get_settings()

        if not settings.newsapi_key:
            return AgentResult(
                source=self.name,
                articles=[],
                fetched_at=datetime.now(),
                error="NEWSAPI_KEY not configured",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    NEWSAPI_URL,
                    params={"category": "technology", "language": "en", "pageSize": LIMIT},
                    headers={"X-Api-Key": settings.newsapi_key},
                )
                resp.raise_for_status()
                raw = resp.json().get("articles", [])

                articles = [
                    Article(
                        title=a["title"],
                        url=a["url"],
                        source=self.name,
                        published_at=datetime.fromisoformat(
                            a["publishedAt"].replace("Z", "+00:00")
                        ),
                        summary=a.get("description"),
                    )
                    for a in raw
                    if a.get("title") not in (None, "[Removed]")
                    and a.get("url") not in (None, "[Removed]")
                ]

        except Exception as e:
            return AgentResult(
                source=self.name,
                articles=[],
                fetched_at=datetime.now(),
                error=str(e),
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
