# Section 4 Design — BaseAgent + Agents

**Project:** news-agent  
**Date:** 2026-05-08  
**Status:** Approved  

---

## Scope

This spec covers four files:

- `news_agent/agents/base.py` — BaseAgent ABC
- `news_agent/agents/hackernews.py` — HackerNewsAgent
- `news_agent/agents/github.py` — GitHubAgent
- `news_agent/agents/newsapi.py` — NewsAPIAgent

---

## Design decisions

| Decision | Choice | Reason |
|---|---|---|
| Articles per source | 10 (fixed) | YAGNI — configurable limit adds complexity without portfolio value |
| HTTP client | Per-agent `async with httpx.AsyncClient` | Full isolation, no coupling to orchestrator |
| HTTP timeout | 10 seconds | Fail fast, graceful degradation |
| GitHub source | Search API with language filter | Official API, no scraping fragility |
| NewsAPI endpoint | `/v2/top-headlines?category=technology` | Aligned with portal-style product vision |

---

## BaseAgent (`agents/base.py`)

Defines the contract all agents implement:

```python
class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AgentResult:
        """Fetch and normalize data. Never raises exceptions."""
        ...
```

**Error pattern:** each subclass wraps all fetch logic in `try/except Exception` and returns `AgentResult(error=str(e), articles=[])` on failure. Exceptions never propagate. The orchestrator only needs to check `result.error is not None` to log.

---

## HackerNewsAgent (`agents/hackernews.py`)

**API:** HackerNews Firebase API — no authentication, no rate limit.

**Fetch flow:**
1. GET `https://hacker-news.firebaseio.com/v0/topstories.json` → list of IDs
2. Take first 10 IDs
3. Fetch each item in parallel via `asyncio.gather`: GET `https://hacker-news.firebaseio.com/v0/item/{id}.json`
4. Filter out items with no `url` (text posts, Ask HN, etc.)
5. Normalize to `Article`

**Article mapping:**
- `title` = `item["title"]`
- `url` = `item["url"]`
- `source` = `"hackernews"`
- `score` = `item["score"]`
- `published_at` = `datetime.fromtimestamp(item["time"])`
- `summary` = `None`

---

## GitHubAgent (`agents/github.py`)

**API:** GitHub Search REST API (`/search/repositories`) — token optional.

**Query parameters:**
```
q=language:python OR language:typescript OR language:go created:>YYYY-MM-DD
sort=stars
order=desc
per_page=10
```

`YYYY-MM-DD` = `(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")`, computed at fetch time.

**Authentication:**
```python
headers = {"Authorization": f"Bearer {token}"} if token else {}
```

Without token: 60 req/h (sufficient). With token: 5000 req/h.

**Article mapping:**
- `title` = `repo["full_name"]` (e.g. `"openai/openai-python"`)
- `url` = `repo["html_url"]`
- `source` = `"github"`
- `score` = `repo["stargazers_count"]`
- `summary` = `repo["description"]` (may be `None`)
- `published_at` = `datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))`

---

## NewsAPIAgent (`agents/newsapi.py`)

**API:** NewsAPI `/v2/top-headlines` — `NEWSAPI_KEY` required.

**Auto-skip:** if `settings.newsapi_key is None`, returns immediately:
```python
AgentResult(source="newsapi", articles=[], fetched_at=datetime.now(), error="NEWSAPI_KEY not configured")
```
No HTTP request is made.

**Query parameters:**
```
category=technology&language=en&pageSize=10
```

**Authentication:** header `X-Api-Key: {newsapi_key}`.

**Article mapping:**
- `title` = `article["title"]`
- `url` = `article["url"]`
- `source` = `"newsapi"`
- `published_at` = `datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))`
- `summary` = `article["description"]` (may be `None`)
- `score` = `None`

**Filtering:** discard articles where `title` or `url` is `None` or `"[Removed]"`.

---

## Testing approach

Each agent is tested with `pytest-asyncio` and `respx` (httpx mock library) to intercept HTTP calls without making real requests.

Tests cover:
- Happy path: returns correct `AgentResult` with normalized `Article` list
- API error (non-200 response): returns `AgentResult(error=...)` with empty articles
- Network timeout: returns `AgentResult(error=...)` gracefully
- NewsAPIAgent with missing key: returns `AgentResult(error="NEWSAPI_KEY not configured")` without HTTP call

---

## Decisions not made in this section

- Orchestrator `asyncio.gather` logic (Section 5)
- How agents are registered with the orchestrator (Section 5)
