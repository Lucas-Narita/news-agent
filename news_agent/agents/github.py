from datetime import datetime, timedelta, timezone

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.retry import with_retry
from news_agent.schemas.models import AgentResult, Article

GITHUB_API = "https://api.github.com/search/repositories"
LANGUAGES = "language:python OR language:typescript OR language:go"
LIMIT = 10


class GitHubAgent(BaseAgent):
    name = "github"

    async def fetch(self) -> AgentResult:
        settings = get_settings()
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        headers = (
            {"Authorization": f"Bearer {settings.github_token}"} if settings.github_token else {}
        )

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:

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

                articles = [
                    Article(
                        title=repo["full_name"],
                        url=repo["html_url"],
                        source=self.name,
                        score=repo["stargazers_count"],
                        summary=repo.get("description"),
                        published_at=datetime.fromisoformat(
                            repo["created_at"].replace("Z", "+00:00")
                        ),
                    )
                    for repo in repos
                ]

        except Exception as e:
            return AgentResult(
                source=self.name,
                articles=[],
                fetched_at=datetime.now(timezone.utc),
                error=str(e),
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now(timezone.utc))
