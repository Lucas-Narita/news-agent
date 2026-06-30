from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import AgentResult, Article

REDDIT_URL = "https://www.reddit.com/r/programming/hot.json"
USER_AGENT = "news-agent/0.1 (tech digest bot)"
LIMIT = 10


class RedditAgent(BaseAgent):
    name = "reddit"

    async def fetch(self) -> AgentResult:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:

                async def _get():
                    resp = await client.get(
                        REDDIT_URL,
                        params={"limit": LIMIT},
                        headers={"User-Agent": USER_AGENT},
                    )
                    resp.raise_for_status()
                    return resp

                resp = await with_retry(_get)
                children = resp.json()["data"]["children"]

                articles = [
                    Article(
                        title=child["data"]["title"],
                        url=child["data"]["url"],
                        source=self.name,
                        score=child["data"].get("score"),
                        published_at=datetime.fromtimestamp(child["data"]["created_utc"]),
                    )
                    for child in children
                    if child["data"].get("url")
                ]

        except Exception as e:
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(), error=str(e)
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
