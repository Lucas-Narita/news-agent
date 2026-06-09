# Sections 5–8: Orchestrator, LLM Client, Output Formatter, README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the orchestrator, LLM client, output formatter, and README to make `news-agent run` produce a real Markdown digest powered by Claude.

**Architecture:** `output/markdown.py` (pure formatter) → `llm/prompts.py` + `llm/client.py` (Claude API call with prompt caching) → `orchestrator.py` (asyncio.gather + graceful degradation) → CLI (already implemented, unchanged). Each layer tested in isolation via mocks.

**Tech Stack:** Python 3.11+, anthropic SDK (AsyncAnthropic), asyncio, pytest-asyncio, unittest.mock

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `news_agent/output/markdown.py` | Create | Pure function: format articles → Markdown string for LLM context |
| `news_agent/llm/prompts.py` | Create | SYSTEM_PROMPT constant + build_user_message() |
| `news_agent/llm/client.py` | Create | generate_narrative(): calls Claude API with prompt caching |
| `news_agent/orchestrator.py` | Replace stub | run_digest(): asyncio.gather + graceful degradation + LLM call |
| `tests/output/__init__.py` | Create | Package marker |
| `tests/output/test_markdown.py` | Create | Tests for format_articles() |
| `tests/llm/__init__.py` | Create | Package marker |
| `tests/llm/test_client.py` | Create | Tests for generate_narrative() via mocked AsyncAnthropic |
| `tests/test_orchestrator.py` | Create | Tests for run_digest() via mocked agents + mocked LLM |
| `README.md` | Create | Setup, usage, architecture overview |

---

## Task 1: Output Formatter

**Files:**
- Create: `news_agent/output/markdown.py`
- Create: `tests/output/__init__.py`
- Create: `tests/output/test_markdown.py`

- [ ] **Step 1: Create package marker**

Create `tests/output/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing tests**

Create `tests/output/test_markdown.py`:

```python
import pytest

from news_agent.schemas.models import Article


def _article(
    source: str,
    title: str = "Title",
    score: int | None = None,
    summary: str | None = None,
) -> Article:
    return Article(title=title, url="https://example.com", source=source, score=score, summary=summary)


def test_format_articles_empty_list():
    from news_agent.output.markdown import format_articles
    assert format_articles([]) == ""


def test_format_articles_groups_by_source():
    from news_agent.output.markdown import format_articles
    articles = [
        _article("hackernews", title="HN Story"),
        _article("github", title="owner/repo"),
    ]
    result = format_articles(articles)
    assert "## Hackernews" in result
    assert "## Github" in result
    assert "HN Story" in result
    assert "owner/repo" in result


def test_format_articles_github_shows_stars():
    from news_agent.output.markdown import format_articles
    articles = [_article("github", title="owner/repo", score=1200)]
    result = format_articles(articles)
    assert "★1200" in result


def test_format_articles_hackernews_shows_score():
    from news_agent.output.markdown import format_articles
    articles = [_article("hackernews", title="HN Story", score=342)]
    result = format_articles(articles)
    assert "(score: 342)" in result


def test_format_articles_includes_summary():
    from news_agent.output.markdown import format_articles
    articles = [_article("newsapi", title="News Title", summary="A brief description.")]
    result = format_articles(articles)
    assert "A brief description." in result


def test_format_articles_no_score_no_decoration():
    from news_agent.output.markdown import format_articles
    articles = [_article("newsapi", title="News Title")]
    result = format_articles(articles)
    assert "(score:" not in result
    assert "★" not in result
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/output/test_markdown.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `format_articles` doesn't exist yet.

- [ ] **Step 4: Implement format_articles**

Create `news_agent/output/markdown.py`:

```python
from news_agent.schemas.models import Article


def format_articles(articles: list[Article]) -> str:
    if not articles:
        return ""

    by_source: dict[str, list[Article]] = {}
    for article in articles:
        by_source.setdefault(article.source, []).append(article)

    sections = []
    for source, items in by_source.items():
        lines = [f"## {source.capitalize()}"]
        for a in items:
            if source == "github":
                line = f"- **{a.title}** ★{a.score} — {a.url}"
            elif a.score is not None:
                line = f"- **{a.title}** (score: {a.score}) — {a.url}"
            else:
                line = f"- **{a.title}** — {a.url}"
            if a.summary:
                line += f"\n  {a.summary}"
            lines.append(line)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
.venv/bin/pytest tests/output/test_markdown.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Run full suite to confirm no regressions**

```bash
.venv/bin/pytest tests/ -q
```

Expected: all previous tests + 6 new = 40 passed.

- [ ] **Step 7: Commit**

```bash
git add news_agent/output/markdown.py tests/output/__init__.py tests/output/test_markdown.py
git commit -m "feat: add format_articles output formatter"
```

---

## Task 2: LLM Prompts

**Files:**
- Create: `news_agent/llm/prompts.py`

No tests — this module contains only constants and a trivial string wrapper. It will be exercised indirectly via the client tests in Task 3.

- [ ] **Step 1: Create prompts.py**

Create `news_agent/llm/prompts.py`:

```python
SYSTEM_PROMPT = """You are a tech news editor. Given a curated list of articles from HackerNews, GitHub Trending, and NewsAPI, generate a concise Markdown digest.

Output format:
# Tech Digest — {today}
**Sources:** {sources}

## Overview
One short paragraph summarizing the main themes across all sources.

## Highlights

### HackerNews
- Bullet points for the most noteworthy stories with a one-line take

### GitHub
- Bullet points for trending repos: what it does and why it stands out

### NewsAPI
- Bullet points for top headlines with context

## Trends
One short paragraph on emerging patterns or recurring topics across sources.

Rules:
- Be concise and factual — no filler phrases
- Use only the articles provided — do not invent URLs, names, or stories
- Keep the total digest under 500 words
- Omit a section entirely if no articles were provided for that source
"""


def build_user_message(articles_markdown: str) -> str:
    return f"Generate a digest from the articles below:\n\n{articles_markdown}"
```

- [ ] **Step 2: Commit**

```bash
git add news_agent/llm/prompts.py
git commit -m "feat: add LLM prompt templates"
```

---

## Task 3: LLM Client

**Files:**
- Create: `news_agent/llm/client.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_client.py`

- [ ] **Step 1: Create package marker**

Create `tests/llm/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing tests**

Create `tests/llm/test_client.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

from news_agent.schemas.models import Article


def _make_article(source: str = "hackernews") -> Article:
    return Article(title="Test Story", url="https://example.com", source=source)


def _mock_response(text: str = "# Digest\nTop stories.") -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


async def test_generate_narrative_returns_text(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response("# Digest\nTop stories."))
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative
        result = await generate_narrative([_make_article()], settings)

    assert result == "# Digest\nTop stories."


async def test_generate_narrative_uses_cache_control(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response())
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative
        await generate_narrative([_make_article()], settings)

    call_kwargs = mock_create.call_args.kwargs
    system = call_kwargs["system"]
    assert any(
        block.get("cache_control") == {"type": "ephemeral"}
        for block in system
    )


async def test_generate_narrative_uses_correct_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    mock_create = AsyncMock(return_value=_mock_response())
    with patch("news_agent.llm.client.anthropic.AsyncAnthropic") as MockClient:
        MockClient.return_value.messages.create = mock_create
        from news_agent.llm.client import generate_narrative
        await generate_narrative([_make_article()], settings)

    assert mock_create.call_args.kwargs["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/llm/test_client.py -v
```

Expected: `ImportError` — `news_agent.llm.client` doesn't exist yet.

- [ ] **Step 4: Implement generate_narrative**

Create `news_agent/llm/client.py`:

```python
import anthropic

from news_agent.config import Settings
from news_agent.llm.prompts import SYSTEM_PROMPT, build_user_message
from news_agent.output.markdown import format_articles
from news_agent.schemas.models import Article


async def generate_narrative(articles: list[Article], settings: Settings) -> str:
    articles_markdown = format_articles(articles)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": build_user_message(articles_markdown)}],
    )
    return response.content[0].text
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
.venv/bin/pytest tests/llm/test_client.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Run full suite to confirm no regressions**

```bash
.venv/bin/pytest tests/ -q
```

Expected: all previous tests + 3 new passed.

- [ ] **Step 7: Commit**

```bash
git add news_agent/llm/client.py news_agent/llm/prompts.py tests/llm/__init__.py tests/llm/test_client.py
git commit -m "feat: implement LLM client with prompt caching"
```

---

## Task 4: Orchestrator

**Files:**
- Modify: `news_agent/orchestrator.py` (replace stub)
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_orchestrator.py`:

```python
from datetime import datetime
from unittest.mock import AsyncMock, patch

from news_agent.schemas.models import AgentResult, Article


def _ok_result(source: str, n: int = 3) -> AgentResult:
    articles = [
        Article(title=f"{source} story {i}", url=f"https://example.com/{i}", source=source)
        for i in range(n)
    ]
    return AgentResult(source=source, articles=articles, fetched_at=datetime.now())


def _err_result(source: str) -> AgentResult:
    return AgentResult(
        source=source, articles=[], fetched_at=datetime.now(), error="API failed"
    )


async def test_run_digest_aggregates_all_sources(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    with (
        patch("news_agent.orchestrator.HackerNewsAgent.fetch", new=AsyncMock(return_value=_ok_result("hackernews"))),
        patch("news_agent.orchestrator.GitHubAgent.fetch", new=AsyncMock(return_value=_ok_result("github"))),
        patch("news_agent.orchestrator.NewsAPIAgent.fetch", new=AsyncMock(return_value=_ok_result("newsapi"))),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# Digest")),
    ):
        from news_agent.orchestrator import run_digest
        result = await run_digest(["hackernews", "github", "newsapi"], settings)

    assert result.total_articles == 9
    assert set(result.sources_used) == {"hackernews", "github", "newsapi"}
    assert result.narrative == "# Digest"


async def test_run_digest_skips_failed_source(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    with (
        patch("news_agent.orchestrator.HackerNewsAgent.fetch", new=AsyncMock(return_value=_ok_result("hackernews"))),
        patch("news_agent.orchestrator.GitHubAgent.fetch", new=AsyncMock(return_value=_err_result("github"))),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# Digest")),
    ):
        from news_agent.orchestrator import run_digest
        result = await run_digest(["hackernews", "github"], settings)

    assert "github" not in result.sources_used
    assert "hackernews" in result.sources_used
    assert result.total_articles == 3


async def test_run_digest_all_sources_fail_skips_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    mock_llm = AsyncMock(return_value="# Digest")
    with (
        patch("news_agent.orchestrator.HackerNewsAgent.fetch", new=AsyncMock(return_value=_err_result("hackernews"))),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest
        result = await run_digest(["hackernews"], settings)

    assert result.total_articles == 0
    assert result.sources_used == []
    assert "No articles available" in result.narrative
    mock_llm.assert_not_called()


async def test_run_digest_calls_generate_narrative_with_articles(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings
    settings = get_settings()

    mock_llm = AsyncMock(return_value="# Digest")
    with (
        patch("news_agent.orchestrator.HackerNewsAgent.fetch", new=AsyncMock(return_value=_ok_result("hackernews", n=2))),
        patch("news_agent.orchestrator.generate_narrative", new=mock_llm),
    ):
        from news_agent.orchestrator import run_digest
        await run_digest(["hackernews"], settings)

    mock_llm.assert_called_once()
    articles_arg = mock_llm.call_args.args[0]
    assert len(articles_arg) == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/test_orchestrator.py -v
```

Expected: FAIL — `run_digest` raises `NotImplementedError`.

- [ ] **Step 3: Implement run_digest**

Replace the entire content of `news_agent/orchestrator.py`:

```python
import asyncio
from datetime import datetime

from news_agent.agents.github import GitHubAgent
from news_agent.agents.hackernews import HackerNewsAgent
from news_agent.agents.newsapi import NewsAPIAgent
from news_agent.config import Settings
from news_agent.llm.client import generate_narrative
from news_agent.schemas.models import Article, DigestOutput

_REGISTRY = {
    "hackernews": HackerNewsAgent,
    "github": GitHubAgent,
    "newsapi": NewsAPIAgent,
}


async def run_digest(sources: list[str], settings: Settings) -> DigestOutput:
    agents = [_REGISTRY[s]() for s in sources if s in _REGISTRY]
    results = await asyncio.gather(*[agent.fetch() for agent in agents])

    articles: list[Article] = []
    sources_used: list[str] = []
    for result in results:
        if result.error is None:
            articles.extend(result.articles)
            sources_used.append(result.source)

    if not articles:
        return DigestOutput(
            narrative="No articles available. All sources failed or returned no results.",
            sources_used=[],
            total_articles=0,
            generated_at=datetime.now(),
        )

    narrative = await generate_narrative(articles, settings)

    return DigestOutput(
        narrative=narrative,
        sources_used=sources_used,
        total_articles=len(articles),
        generated_at=datetime.now(),
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
.venv/bin/pytest tests/test_orchestrator.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
.venv/bin/pytest tests/ -q
```

Expected: all tests pass (previous 40 + 4 new = 44 passed).

- [ ] **Step 6: Commit**

```bash
git add news_agent/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: implement orchestrator with graceful degradation"
```

---

## Task 5: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

Create `README.md` at the project root:

```markdown
# news-agent

CLI that aggregates tech news from HackerNews, GitHub Trending, and NewsAPI, then generates a Markdown digest using Claude.

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- (Optional) A [NewsAPI key](https://newsapi.org/) and a [GitHub token](https://github.com/settings/tokens)

## Setup

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy and fill in your keys
cp .env.example .env
```

`.env` variables:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `NEWSAPI_KEY` | No | NewsAPI key — enables the newsapi source |
| `GITHUB_TOKEN` | No | GitHub token — raises rate limit from 60 to 5000 req/h |

## Usage

```bash
# Generate a digest from all available sources
news-agent run

# Use specific sources
news-agent run --sources hackernews,github

# Print to terminal only, skip saving the .md file
news-agent run --no-file

# Check configuration status
news-agent config check
```

Digests are saved to `output/digest-YYYY-MM-DD-HH.md` by default.

## Architecture

```
CLI (Typer)
 └─► Orchestrator
       ├─► HackerNewsAgent  ─┐
       ├─► GitHubAgent       ├─► asyncio.gather() → AgentResult[]
       └─► NewsAPIAgent     ─┘
             │
             ▼
        LLM Client (Claude API, claude-sonnet-4-6)
             │
             ▼
     output/digest-YYYY-MM-DD-HH.md + terminal (rich)
```

Each agent is independent — the orchestrator only calls `.fetch()` and receives `AgentResult`. Errors are captured in `AgentResult.error`; the system degrades gracefully if a source fails.

## Running Tests

```bash
pytest tests/
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage"
```

---

## Final Verification

- [ ] **Run the complete test suite one last time**

```bash
.venv/bin/pytest tests/ -v
```

Expected: 44 tests, all passed.

- [ ] **Smoke test the CLI wiring (no real API keys needed)**

```bash
ANTHROPIC_API_KEY=sk-fake .venv/bin/news-agent config check
```

Expected: table with `ANTHROPIC_API_KEY OK` and the two optional keys as `OPTIONAL`.
