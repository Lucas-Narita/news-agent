import asyncio
from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.schemas.models import AgentResult, Article

HN_BASE = "https://hacker-news.firebaseio.com/v0"
LIMIT = 10


class HackerNewsAgent(BaseAgent):
    name = "hackernews"

    async def fetch(self) -> AgentResult:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{HN_BASE}/topstories.json")
                resp.raise_for_status()
                ids = resp.json()[:LIMIT]

                async def fetch_item(item_id: int) -> dict | None:
                    try:
                        r = await client.get(f"{HN_BASE}/item/{item_id}.json")
                        r.raise_for_status()
                        return r.json()
                    except Exception:
                        return None

                items = await asyncio.gather(*[fetch_item(i) for i in ids])

                articles = [
                    Article(
                        title=item["title"],
                        url=item["url"],
                        source=self.name,
                        score=item.get("score"),
                        published_at=datetime.fromtimestamp(item["time"]),
                    )
                    for item in items
                    if item and item.get("url")
                ]

        except Exception as e:
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(), error=str(e)
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
