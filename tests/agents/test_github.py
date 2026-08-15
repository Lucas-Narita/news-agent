import httpx
import respx

GITHUB_API = "https://api.github.com/search/repositories"


def _make_repo(i: int) -> dict:
    return {
        "full_name": f"owner/repo-{i}",
        "html_url": f"https://github.com/owner/repo-{i}",
        "stargazers_count": 1000 + i,
        "description": f"Description {i}",
        "created_at": "2026-05-01T00:00:00Z",
    }


def _github_response(n: int = 10) -> httpx.Response:
    return httpx.Response(200, json={"items": [_make_repo(i) for i in range(n)], "total_count": n})


async def test_github_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with respx.mock:
        respx.get(GITHUB_API).mock(return_value=_github_response())

        from news_agent.agents.github import GitHubAgent

        agent = GitHubAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "github"
    assert len(result.articles) == 10
    assert result.articles[0].title == "owner/repo-0"
    assert result.articles[0].source == "github"
    assert result.articles[0].score == 1000


async def test_github_sends_auth_header_when_token_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-mytoken")

    with respx.mock:
        route = respx.get(GITHUB_API).mock(return_value=_github_response())

        from news_agent.agents.github import GitHubAgent

        agent = GitHubAgent()
        await agent.fetch()

    assert route.called
    assert "Bearer ghp-mytoken" in route.calls[0].request.headers.get("authorization", "")


async def test_github_no_auth_header_without_token(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with respx.mock:
        route = respx.get(GITHUB_API).mock(return_value=_github_response())

        from news_agent.agents.github import GitHubAgent

        agent = GitHubAgent()
        await agent.fetch()

    assert route.called
    assert "authorization" not in route.calls[0].request.headers


async def test_github_api_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    with respx.mock:
        respx.get(GITHUB_API).mock(return_value=httpx.Response(403))

        from news_agent.agents.github import GitHubAgent

        agent = GitHubAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_github_network_timeout(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    with respx.mock:
        respx.get(GITHUB_API).mock(side_effect=httpx.TimeoutException("timeout"))

        from news_agent.agents.github import GitHubAgent

        agent = GitHubAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_github_retries_on_transient_error(monkeypatch):
    """A 503 on the first attempt is retried and recovers on the second."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with respx.mock:
        respx.get(GITHUB_API).mock(side_effect=[httpx.Response(503), _github_response()])

        from news_agent.agents.github import GitHubAgent

        agent = GitHubAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 10


async def test_github_skips_repos_missing_required_fields():
    """One malformed repo in the page must not discard the other nine."""
    from news_agent.agents.github import GitHubAgent

    broken = {"full_name": "owner/broken"}  # no html_url, no created_at
    payload = {"items": [_make_repo(1), broken], "total_count": 2}

    with respx.mock:
        respx.get(GITHUB_API).mock(return_value=httpx.Response(200, json=payload))

        result = await GitHubAgent().fetch()

    assert result.error is None
    assert len(result.articles) == 1
