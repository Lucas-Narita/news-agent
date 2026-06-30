from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import AgentResult, Article

DEVTO_URL = "https://dev.to/api/articles"
LIMIT = 10
TOP_DAYS = 7


class DevToAgent(BaseAgent):
    name = "devto"

    async def fetch(self) -> AgentResult:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:

                async def _get():
                    resp = await client.get(DEVTO_URL, params={"per_page": LIMIT, "top": TOP_DAYS})
                    resp.raise_for_status()
                    return resp

                resp = await with_retry(_get)
                raw = resp.json()

                articles = [
                    Article(
                        title=item["title"],
                        url=item["url"],
                        source=self.name,
                        score=item.get("positive_reactions_count"),
                        summary=item.get("description"),
                        published_at=datetime.fromisoformat(
                            item["published_at"].replace("Z", "+00:00")
                        ),
                    )
                    for item in raw
                    if item.get("url")
                ]

        except Exception as e:
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(), error=str(e)
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
