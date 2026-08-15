from unittest.mock import AsyncMock

import httpx
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


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


async def test_with_retry_does_not_retry_client_errors(monkeypatch):
    """A 4xx is permanent — fail fast instead of retrying."""
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        raise _status_error(403)

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(op, retries=3, base_delay=0.5)

    assert calls == 1  # no retry for a client error
    sleep_mock.assert_not_awaited()


async def test_with_retry_retries_server_errors(monkeypatch):
    """A 5xx is worth retrying."""
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    calls = 0

    async def op():
        nonlocal calls
        calls += 1
        raise _status_error(503)

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(op, retries=3, base_delay=0.5)

    assert calls == 3  # retried up to the limit


async def test_with_retry_caps_the_backoff_delay(monkeypatch):
    """Doubling must not grow past max_delay, however many retries are allowed."""
    sleep_mock = AsyncMock()
    monkeypatch.setattr("news_agent.retry.sleep", sleep_mock)

    async def op():
        raise ConnectionError("always down")

    with pytest.raises(ConnectionError):
        await with_retry(op, retries=6, base_delay=1.0, max_delay=4.0)

    delays = [call.args[0] for call in sleep_mock.await_args_list]
    assert delays == [1.0, 2.0, 4.0, 4.0, 4.0]


async def test_with_retry_logs_each_retry(monkeypatch, caplog):
    """A retried source should be visible under --verbose, not silent."""
    monkeypatch.setattr("news_agent.retry.sleep", AsyncMock())

    attempts = 0

    async def op():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("transient")
        return "ok"

    with caplog.at_level("INFO", logger="news_agent.retry"):
        assert await with_retry(op, retries=3, base_delay=0.5) == "ok"

    assert "retrying in" in caplog.text
