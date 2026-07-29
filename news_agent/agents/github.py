from datetime import datetime, timedelta, timezone

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

GITHUB_API = "https://api.github.com/search/repositories"
LANGUAGES = "language:python OR language:typescript OR language:go"
LIMIT = 10
TRENDING_WINDOW_DAYS = 7


class GitHubAgent(BaseAgent):
    name = "github"

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        settings = get_settings()
        since = (datetime.now(timezone.utc) - timedelta(days=TRENDING_WINDOW_DAYS)).strftime(
            "%Y-%m-%d"
        )
        headers = (
            {"Authorization": f"Bearer {settings.github_token}"} if settings.github_token else {}
        )

        async def _get():
            resp = await client.get(
                GITHUB_API,
                params={
                    "q": f"{LANGUAGES} created:>{since}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": LIMIT,
                },
                headers=headers,
            )
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        repos = resp.json()["items"]

        return [
            Article(
                title=repo["full_name"],
                url=repo["html_url"],
                source=self.name,
                score=repo["stargazers_count"],
                summary=repo.get("description"),
                published_at=datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00")),
            )
            for repo in repos
        ]
