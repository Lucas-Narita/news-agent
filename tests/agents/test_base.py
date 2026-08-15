"""Behaviour BaseAgent provides to every agent, tested through one concrete agent."""

import httpx
import respx

LOBSTERS_URL = "https://lobste.rs/hottest.json"


async def test_every_request_carries_an_identifying_user_agent():
    """Reddit rejects the default httpx User-Agent; the shared client sets ours."""
    from news_agent.agents.lobsters import LobstersAgent

    with respx.mock:
        route = respx.get(LOBSTERS_URL).mock(return_value=httpx.Response(200, json=[]))

        await LobstersAgent().fetch()

    sent = route.calls.last.request.headers["User-Agent"]
    assert sent.startswith("news-agent/")
    assert "github.com/Lucas-Narita/news-agent" in sent


async def test_fetch_honours_the_configured_request_timeout(monkeypatch):
    monkeypatch.setenv("REQUEST_TIMEOUT", "2.5")
    from news_agent.agents.lobsters import LobstersAgent

    with respx.mock:
        route = respx.get(LOBSTERS_URL).mock(return_value=httpx.Response(200, json=[]))

        await LobstersAgent().fetch()

    assert route.calls.last.request.extensions["timeout"]["connect"] == 2.5


async def test_fetch_never_raises_on_a_transport_error():
    """The whole contract: agents report failure as data, never as an exception."""
    from news_agent.agents.lobsters import LobstersAgent

    with respx.mock:
        respx.get(LOBSTERS_URL).mock(side_effect=httpx.ConnectError("no route to host"))

        result = await LobstersAgent().fetch()

    assert result.error is not None
    assert result.articles == []
    assert result.source == "lobsters"
