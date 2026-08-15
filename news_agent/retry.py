"""Generic async retry with exponential backoff.

Network calls to external APIs fail transiently (timeouts, 5xx, dropped
connections). This helper retries any awaitable operation, doubling the delay
between attempts, so a brief blip does not cost the whole source.
"""

import logging
from asyncio import sleep
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Doubling is unbounded by nature; with the default 10s request timeout a
# single source could otherwise stall the whole gather() far longer than the
# digest is worth waiting for.
MAX_DELAY = 8.0


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = MAX_DELAY,
) -> T:
    """Run ``operation``, retrying on exception with exponential backoff.

    Tries up to ``retries`` times. After a failed attempt it sleeps
    ``min(base_delay * 2**attempt, max_delay)`` seconds before the next one. If
    every attempt fails, the last exception propagates to the caller.
    """
    for attempt in range(retries):
        try:
            return await operation()
        except Exception as exc:
            # 4xx responses are permanent (bad request, auth, not found, rate limit) —
            # retrying only wastes time and can make rate limiting worse.
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                raise
            if attempt == retries - 1:
                raise
            delay = min(base_delay * (2**attempt), max_delay)
            logger.info(
                "attempt %d/%d failed (%s); retrying in %.1fs",
                attempt + 1,
                retries,
                exc,
                delay,
            )
            await sleep(delay)
    raise RuntimeError("with_retry called with retries < 1")  # pragma: no cover
