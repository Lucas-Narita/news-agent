import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from time import perf_counter

import httpx

from news_agent.config import get_settings
from news_agent.schemas.models import AgentResult, Article

logger = logging.getLogger(__name__)


def _user_agent() -> str:
    """Identify the client to every upstream API.

    Reddit rejects the default httpx User-Agent outright, and the others treat
    an identifiable client more kindly under rate limiting. Setting it once on
    the shared client means a new agent inherits it for free.
    """
    try:
        release = version("news-agent")
    except PackageNotFoundError:  # pragma: no cover - only when running from source
        release = "dev"
    return f"news-agent/{release} (+https://github.com/Lucas-Narita/news-agent)"


USER_AGENT = _user_agent()


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
        started = perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=settings.request_timeout,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                articles = await self._fetch_articles(client)
        except Exception as e:
            # Timing the failure too: "which source is making the digest slow"
            # is the first question when a scheduled run starts timing out.
            logger.info("%s failed after %.2fs: %s", self.name, perf_counter() - started, e)
            return AgentResult(
                source=self.name, articles=[], fetched_at=datetime.now(timezone.utc), error=str(e)
            )

        logger.info(
            "%s returned %d articles in %.2fs",
            self.name,
            len(articles),
            perf_counter() - started,
        )
        return AgentResult(
            source=self.name, articles=articles, fetched_at=datetime.now(timezone.utc)
        )
