from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import AgentResult, Article

LOBSTERS_URL = "https://lobste.rs/hottest.json"


class LobstersAgent(BaseAgent):
    name = "lobsters"

    async def fetch(self) -> AgentResult:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:

                async def _get():
                    resp = await client.get(LOBSTERS_URL)
                    resp.raise_for_status()
                    return resp

                resp = await with_retry(_get)
                stories = resp.json()

                articles = [
                    Article(
                        title=story["title"],
                        url=story["url"],
                        source=self.name,
                        score=story.get("score"),
                        published_at=datetime.fromisoformat(story["created_at"]),
                    )
                    for story in stories
                    if story.get("url")
                ]

        except Exception as e:
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(), error=str(e)
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
