from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from news_agent.config import get_settings
from news_agent.schemas.models import AgentResult, Article


class BaseAgent(ABC):
    name: str

    def _precheck(self) -> str | None:
        """Optional guard run before any network call.

        Return an error message to short-circuit fetch() without opening a
        client (e.g. a missing API key); return None to proceed normally.
        """
        return None

    @abstractmethod
    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        """Fetch and parse this source's articles.

        May raise — fetch() converts any exception into AgentResult.error so
        callers never see it.
        """
        ...

    async def fetch(self) -> AgentResult:
        """Fetch and normalize data. Never raises exceptions."""
        precheck_error = self._precheck()
        if precheck_error is not None:
            return AgentResult(
                source=self.name,
                articles=[],
                fetched_at=datetime.now(timezone.utc),
                error=precheck_error,
            )

        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                articles = await self._fetch_articles(client)
        except Exception as e:
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(timezone.utc), error=str(e)
            )

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now(timezone.utc))
