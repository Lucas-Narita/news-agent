from unittest.mock import AsyncMock

import pytest

from news_agent.retry import with_retry


async def test_with_retry_returns_on_first_success(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_retry(op, retries=3, base_delay=0.5)

    assert result == "ok"
    assert calls == 1
    sleep_mock.assert_not_awaited()  # success never sleeps


async def test_with_retry_retries_until_success(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    attempts = 0

    async def op():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("transient")
        return "recovered"

    result = await with_retry(op, retries=3, base_delay=0.5)

    assert result == "recovered"
    assert attempts == 3
    assert sleep_mock.await_count == 2  # slept between the 3 attempts


async def test_with_retry_uses_exponential_backoff(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    async def op():
        raise TimeoutError("always fails")

    with pytest.raises(TimeoutError):
        await with_retry(op, retries=3, base_delay=0.5)

    delays = [call.args[0] for call in sleep_mock.await_args_list]
    assert delays == [0.5, 1.0]  # doubles each attempt


async def test_with_retry_raises_last_exception_after_exhausting(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    async def op():
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        await with_retry(op, retries=2, base_delay=0.1)
