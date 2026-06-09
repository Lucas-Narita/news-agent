# Section 4: BaseAgent + Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement BaseAgent ABC and three concrete agents (HackerNews, GitHub, NewsAPI) that fetch and normalize tech news into `AgentResult` objects, never raising exceptions.

**Architecture:** Each agent owns its own `httpx.AsyncClient`, wraps all logic in `try/except Exception`, and returns `AgentResult(error=...)` on failure. HackerNewsAgent fetches items in parallel via `asyncio.gather`. GitHubAgent uses the Search API filtered by Python/TypeScript/Go. NewsAPIAgent uses `/v2/top-headlines?category=technology` and auto-skips when key is absent.

**Tech Stack:** Python 3.11+, httpx, asyncio, respx (httpx mock for tests), pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add `respx>=0.20` to dev deps |
| `news_agent/agents/base.py` | Create | BaseAgent ABC |
| `news_agent/agents/hackernews.py` | Create | HackerNewsAgent |
| `news_agent/agents/github.py` | Create | GitHubAgent |
| `news_agent/agents/newsapi.py` | Create | NewsAPIAgent |
| `tests/agents/__init__.py` | Create | Package marker |
| `tests/agents/test_hackernews.py` | Create | HackerNews agent tests |
| `tests/agents/test_github.py` | Create | GitHub agent tests |
| `tests/agents/test_newsapi.py` | Create | NewsAPI agent tests |

---

## Task 1: Dev dependency + BaseAgent

**Files:**
- Modify: `pyproject.toml`
- Create: `news_agent/agents/base.py`
- Create: `tests/agents/__init__.py`

No tests — abstract class has no behavior to test directly.

- [ ] **Step 1: Add `respx` to dev dependencies in `pyproject.toml`**

Change the `dev` optional dependencies block to:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "respx>=0.20",
]
```

- [ ] **Step 2: Install the new dependency**

```bash
.venv/bin/pip install respx -q
```

Expected: no errors. Verify: `.venv/bin/python -c "import respx; print('ok')`

- [ ] **Step 3: Create `news_agent/agents/base.py`**

```python
from abc import ABC, abstractmethod

from news_agent.schemas.models import AgentResult


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AgentResult:
        """Fetch and normalize data. Never raises exceptions."""
        ...
```

- [ ] **Step 4: Create `tests/agents/__init__.py`**

```bash
touch tests/agents/__init__.py
```

- [ ] **Step 5: Verify existing tests still pass**

```bash
.venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: 20 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml news_agent/agents/base.py tests/agents/__init__.py
git commit -m "feat: add BaseAgent ABC and respx dev dependency"
```

---

## Task 2: HackerNewsAgent (TDD)

**Files:**
- Create: `tests/agents/test_hackernews.py`
- Create: `news_agent/agents/hackernews.py`

- [ ] **Step 1: Write failing tests**

`tests/agents/test_hackernews.py`:
```python
import re

import httpx
import pytest
import respx

from news_agent.agents.hackernews import HackerNewsAgent

HN_BASE = "https://hacker-news.firebaseio.com/v0"


def _make_item(i: int, has_url: bool = True) -> dict:
    return {
        "id": i,
        "title": f"Story {i}",
        "url": f"https://example.com/{i}" if has_url else None,
        "score": 100 + i,
        "time": 1700000000,
        "type": "story",
    }


async def test_hackernews_happy_path():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            return_value=httpx.Response(200, json=list(range(1, 21)))
        )
        respx.get(re.compile(rf"{re.escape(HN_BASE)}/item/\d+\.json")).mock(
            side_effect=lambda req: httpx.Response(
                200, json=_make_item(int(req.url.path.split("/")[-1].replace(".json", "")))
            )
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "hackernews"
    assert len(result.articles) == 10
    assert result.articles[0].source == "hackernews"
    assert result.articles[0].score == 101


async def test_hackernews_filters_items_without_url():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            return_value=httpx.Response(200, json=[1, 2, 3])
        )
        respx.get(re.compile(rf"{re.escape(HN_BASE)}/item/\d+\.json")).mock(
            side_effect=lambda req: httpx.Response(
                200,
                json=_make_item(
                    int(req.url.path.split("/")[-1].replace(".json", "")),
                    has_url=(int(req.url.path.split("/")[-1].replace(".json", "")) != 2),
                ),
            )
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 2


async def test_hackernews_network_timeout():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_hackernews_api_error():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(
            return_value=httpx.Response(500)
        )

        agent = HackerNewsAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/agents/test_hackernews.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'news_agent.agents.hackernews'`

- [ ] **Step 3: Implement `news_agent/agents/hackernews.py`**

```python
import asyncio
from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.schemas.models import AgentResult, Article

HN_BASE = "https://hacker-news.firebaseio.com/v0"
LIMIT = 10


class HackerNewsAgent(BaseAgent):
    name = "hackernews"

    async def fetch(self) -> AgentResult:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{HN_BASE}/topstories.json")
                resp.raise_for_status()
                ids = resp.json()[:LIMIT]

                async def fetch_item(item_id: int) -> dict | None:
                    try:
                        r = await client.get(f"{HN_BASE}/item/{item_id}.json")
                        r.raise_for_status()
                        return r.json()
                    except Exception:
                        return None

                items = await asyncio.gather(*[fetch_item(i) for i in ids])

                articles = [
                    Article(
                        title=item["title"],
                        url=item["url"],
                        source=self.name,
                        score=item.get("score"),
                        published_at=datetime.fromtimestamp(item["time"]),
                    )
                    for item in items
                    if item and item.get("url")
                ]

        except Exception as e:
            return AgentResult(source=self.name, articles=[], fetched_at=datetime.now(), error=str(e))

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/agents/test_hackernews.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add news_agent/agents/hackernews.py tests/agents/test_hackernews.py
git commit -m "feat: implement HackerNewsAgent with parallel item fetch"
```

---

## Task 3: GitHubAgent (TDD)

**Files:**
- Create: `tests/agents/test_github.py`
- Create: `news_agent/agents/github.py`

- [ ] **Step 1: Write failing tests**

`tests/agents/test_github.py`:
```python
import httpx
import pytest
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/agents/test_github.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'news_agent.agents.github'`

- [ ] **Step 3: Implement `news_agent/agents/github.py`**

```python
from datetime import datetime, timedelta

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
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
            {"Authorization": f"Bearer {settings.github_token}"}
            if settings.github_token
            else {}
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
            return AgentResult(source=self.name, articles=[], fetched_at=datetime.now(), error=str(e))

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/agents/test_github.py -v 2>&1 | tail -10
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add news_agent/agents/github.py tests/agents/test_github.py
git commit -m "feat: implement GitHubAgent with search API and language filter"
```

---

## Task 4: NewsAPIAgent (TDD)

**Files:**
- Create: `tests/agents/test_newsapi.py`
- Create: `news_agent/agents/newsapi.py`

- [ ] **Step 1: Write failing tests**

`tests/agents/test_newsapi.py`:
```python
import httpx
import pytest
import respx

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


def _make_article(i: int, title: str | None = None, url: str | None = None) -> dict:
    return {
        "title": title if title is not None else f"Article {i}",
        "url": url if url is not None else f"https://example.com/article-{i}",
        "publishedAt": "2026-05-08T12:00:00Z",
        "description": f"Description {i}",
    }


def _newsapi_response(articles: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok", "articles": articles})


async def test_newsapi_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    articles = [_make_article(i) for i in range(10)]

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response(articles))

        from news_agent.agents.newsapi import NewsAPIAgent
        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "newsapi"
    assert len(result.articles) == 10
    assert result.articles[0].source == "newsapi"
    assert result.articles[0].title == "Article 0"


async def test_newsapi_auto_skip_when_key_missing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)

    with respx.mock:
        from news_agent.agents.newsapi import NewsAPIAgent
        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error == "NEWSAPI_KEY not configured"
    assert result.articles == []
    assert not respx.calls  # no HTTP call was made


async def test_newsapi_filters_removed_articles(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    articles = [
        _make_article(0),
        _make_article(1, title="[Removed]"),
        _make_article(2, url="[Removed]"),
        _make_article(3, title=None),
        _make_article(4),
    ]

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response(articles))

        from news_agent.agents.newsapi import NewsAPIAgent
        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 2


async def test_newsapi_sends_api_key_header(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "my-secret-key")

    with respx.mock:
        route = respx.get(NEWSAPI_URL).mock(return_value=_newsapi_response([]))

        from news_agent.agents.newsapi import NewsAPIAgent
        agent = NewsAPIAgent()
        await agent.fetch()

    assert route.called
    assert route.calls[0].request.headers.get("x-api-key") == "my-secret-key"


async def test_newsapi_api_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key-test")

    with respx.mock:
        respx.get(NEWSAPI_URL).mock(return_value=httpx.Response(429))

        from news_agent.agents.newsapi import NewsAPIAgent
        agent = NewsAPIAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/agents/test_newsapi.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError: No module named 'news_agent.agents.newsapi'`

- [ ] **Step 3: Implement `news_agent/agents/newsapi.py`**

```python
from datetime import datetime

import httpx

from news_agent.agents.base import BaseAgent
from news_agent.config import get_settings
from news_agent.schemas.models import AgentResult, Article

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"
LIMIT = 10


class NewsAPIAgent(BaseAgent):
    name = "newsapi"

    async def fetch(self) -> AgentResult:
        settings = get_settings()

        if not settings.newsapi_key:
            return AgentResult(
                source=self.name,
                articles=[],
                fetched_at=datetime.now(),
                error="NEWSAPI_KEY not configured",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    NEWSAPI_URL,
                    params={"category": "technology", "language": "en", "pageSize": LIMIT},
                    headers={"X-Api-Key": settings.newsapi_key},
                )
                resp.raise_for_status()
                raw = resp.json().get("articles", [])

                articles = [
                    Article(
                        title=a["title"],
                        url=a["url"],
                        source=self.name,
                        published_at=datetime.fromisoformat(
                            a["publishedAt"].replace("Z", "+00:00")
                        ),
                        summary=a.get("description"),
                    )
                    for a in raw
                    if a.get("title") not in (None, "[Removed]")
                    and a.get("url") not in (None, "[Removed]")
                ]

        except Exception as e:
            return AgentResult(source=self.name, articles=[], fetched_at=datetime.now(), error=str(e))

        return AgentResult(source=self.name, articles=articles, fetched_at=datetime.now())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/agents/test_newsapi.py -v 2>&1 | tail -10
```

Expected: 5 passed.

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest tests/ -v 2>&1 | tail -15
```

Expected: 33 passed (20 previous + 4 HN + 5 GitHub + 5 NewsAPI = 34... wait: 4 + 5 + 5 = 14 new, 20 + 14 = 34 total).

- [ ] **Step 6: Commit**

```bash
git add news_agent/agents/newsapi.py tests/agents/test_newsapi.py
git commit -m "feat: implement NewsAPIAgent with technology category and [Removed] filtering"
```

---

## Self-review

**Spec coverage:**
- BaseAgent ABC → Task 1 ✓
- HackerNewsAgent: parallel fetch, filter no-URL, error handling → Task 2 ✓
- GitHubAgent: Search API, language filter, optional auth → Task 3 ✓
- NewsAPIAgent: top-headlines, auto-skip, filter [Removed] → Task 4 ✓
- HTTP timeout 10s → all agents use `httpx.AsyncClient(timeout=10.0)` ✓
- Per-agent client (no shared client) → each agent uses `async with httpx.AsyncClient` ✓
- `respx` for tests → Task 1 installs, Tasks 2-4 use it ✓

**Placeholders:** none — all steps have complete code.

**Type consistency:**
- `AgentResult(source=self.name, articles=[], fetched_at=datetime.now(), error=str(e))` — consistent across all three agents ✓
- `Article(title=..., url=..., source=self.name, ...)` — consistent field names with `schemas/models.py` ✓
- `BaseAgent.name: str` referenced as `self.name` in all agents ✓
- `datetime.fromisoformat(...replace("Z", "+00:00"))` — consistent ISO 8601 parsing in GitHub and NewsAPI ✓
- `datetime.fromtimestamp(item["time"])` — Unix timestamp for HackerNews ✓
