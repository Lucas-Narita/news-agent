from datetime import datetime, timezone

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import AgentResult, Article

REDDIT_URL = "https://www.reddit.com/r/programming/hot.json"
USER_AGENT = "news-agent/0.1 (tech digest bot)"
LIMIT = 10


def _parse_child(child: dict, source: str) -> Article | None:
    """Build an Article from one Reddit child, or None if the item is malformed.

    Parsing per-item keeps a single bad entry from sinking the whole source.
    """
    try:
        data = child["data"]
        if not data.get("url"):
            return None
        return Article(
            title=data["title"],
            url=data["url"],
            source=source,
            score=data.get("score"),
            published_at=datetime.fromtimestamp(data["created_utc"], tz=timezone.utc),
        )
    except (KeyError, ValueError, TypeError):
        return None


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
                    article
                    for child in children
                    if (article := _parse_child(child, self.name)) is not None
                ]

        except Exception as e:
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(), error=str(e)
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
