from datetime import UTC, datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

REDDIT_URL = "https://www.reddit.com/r/programming/hot.json"
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
            published_at=datetime.fromtimestamp(data["created_utc"], tz=UTC),
        )
    except (KeyError, ValueError, TypeError):
        return None


class RedditAgent(BaseAgent):
    name = "reddit"

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        """Fetch the hot r/programming listing and parse it into articles.

        Malformed children (missing url/title) are skipped individually via
        ``_parse_child``; only a network/HTTP failure propagates to fetch().
        """

        async def _get():
            # User-Agent comes from the shared client configured in BaseAgent.
            resp = await client.get(REDDIT_URL, params={"limit": LIMIT})
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        children = resp.json()["data"]["children"]

        return [
            article for child in children if (article := _parse_child(child, self.name)) is not None
        ]
