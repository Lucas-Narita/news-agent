"""Generic async retry with exponential backoff.

Network calls to external APIs fail transiently (timeouts, 5xx, dropped
connections). This helper retries any awaitable operation, doubling the delay
between attempts, so a brief blip does not cost the whole source.
"""

from asyncio import sleep
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay: float = 0.5,
) -> T:
    """Run ``operation``, retrying on exception with exponential backoff.

    Tries up to ``retries`` times. After a failed attempt it sleeps
    ``base_delay * 2**attempt`` seconds before the next one. If every attempt
    fails, the last exception propagates to the caller.
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
            await sleep(base_delay * (2**attempt))
    raise RuntimeError("with_retry called with retries < 1")  # pragma: no cover
