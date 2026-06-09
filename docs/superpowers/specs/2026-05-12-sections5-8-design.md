# Design: Sections 5–8 — Orchestrator, LLM, Output, Tests, README

**Date:** 2026-05-12
**Branch:** feat/section4-agents
**Status:** Approved

---

## Context

Sections 1–4 and Config/CLI are fully implemented and tested (34 tests, all passing).
This spec covers what remains to make `news-agent run` produce a real digest.

---

## Section 5 — Orchestrator

**File:** `news_agent/orchestrator.py`

`run_digest(sources: list[str], settings: Settings) -> DigestOutput`:

1. Build agent registry: `{"hackernews": HackerNewsAgent, "github": GitHubAgent, "newsapi": NewsAPIAgent}`.
2. Instantiate only agents present in `sources`.
3. `await asyncio.gather(*[agent.fetch() for agent in agents])` → `list[AgentResult]`.
4. Filter out results where `result.error is not None` (graceful degradation — system continues without that source).
5. Flatten `AgentResult.articles` into `list[Article]`.
6. If no articles after degradation → return `DigestOutput` with a "no sources available" narrative.
7. Call `generate_narrative(articles, settings)` from the LLM client.
8. Return `DigestOutput(narrative=..., sources_used=..., total_articles=..., generated_at=...)`.

**Principle:** the orchestrator never knows how each agent works — only calls `.fetch()`.

---

## Section 6 — LLM Client + Prompts

### `news_agent/llm/prompts.py`

Two exports:

- `SYSTEM_PROMPT: str` — static instructions for Claude. Defines role ("you are a tech news editor"), output format (Markdown digest with sections: date/sources header, brief intro, per-source highlights with bullets, closing trend summary), and constraints (be concise, stay factual, use the provided articles only).
- `build_user_message(articles_markdown: str) -> str` — wraps the formatted article block with a simple instruction ("Generate a digest from the articles below:").

### `news_agent/llm/client.py`

`async generate_narrative(articles: list[Article], settings: Settings) -> str`:

1. Calls `format_articles(articles)` from `output.markdown` to build the context block.
2. Creates `anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)`.
3. Sends `messages.create` with:
   - `model="claude-sonnet-4-6"`
   - `max_tokens=1024`
   - `system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]`
   - `messages=[{"role": "user", "content": build_user_message(articles_markdown)}]`
4. Returns `response.content[0].text`.

Prompt caching on `SYSTEM_PROMPT` reduces cost and latency on repeated runs (the system prompt is large and static).

---

## Section 7 — Output Formatter

**File:** `news_agent/output/markdown.py`

`format_articles(articles: list[Article]) -> str`:

- Pure function, no I/O.
- Groups articles by `article.source`.
- Produces a Markdown block used as LLM context (not for final output):

```
## HackerNews
- **Story Title** (score: 342) — https://example.com
  ...

## GitHub
- **owner/repo** ★1200 — https://github.com/...
  Description of the repo.
  ...

## NewsAPI
- **Article Title** — https://example.com
  Summary sentence.
  ...
```

The CLI keeps ownership of writing `.md` files and printing to the terminal.

---

## Section 8 — Tests

### `tests/test_orchestrator.py`

- `test_run_digest_aggregates_all_sources` — mock all three agents, assert `DigestOutput` has correct counts.
- `test_run_digest_skips_failed_source` — one agent returns `error`, assert it's excluded from `sources_used`.
- `test_run_digest_all_sources_fail` — all agents fail, assert fallback narrative is returned without calling LLM.
- `test_run_digest_calls_generate_narrative` — patch `generate_narrative`, assert it's called with the aggregated articles.

### `tests/llm/test_client.py`

- `test_generate_narrative_returns_text` — mock `AsyncAnthropic`, assert the returned string matches the mocked response.
- `test_generate_narrative_uses_cache_control` — assert the system message block has `cache_control`.
- `test_generate_narrative_uses_correct_model` — assert `model="claude-sonnet-4-6"` in the API call.

### `tests/output/test_markdown.py`

- `test_format_articles_groups_by_source` — articles from two sources, assert both sections present.
- `test_format_articles_empty_list` — returns empty string or minimal header, no crash.
- `test_format_articles_github_shows_stars` — GitHub article with score, assert `★` in output.

### README

- Project description (one paragraph).
- Prerequisites: Python 3.11+, API keys.
- Setup: `pip install -e ".[dev]"`, `.env` config.
- Usage: `news-agent run`, `news-agent run --sources hackernews,github`, `news-agent config check`.
- Architecture overview (brief — points to CLAUDE.md for full detail).

---

## File Map

| File | Action |
|---|---|
| `news_agent/orchestrator.py` | Replace stub with real implementation |
| `news_agent/llm/prompts.py` | Create |
| `news_agent/llm/client.py` | Create |
| `news_agent/output/markdown.py` | Create |
| `tests/test_orchestrator.py` | Create |
| `tests/llm/__init__.py` | Create |
| `tests/llm/test_client.py` | Create |
| `tests/output/__init__.py` | Create |
| `tests/output/test_markdown.py` | Create |
| `README.md` | Create |

---

## Non-Goals

- Não adicionar `--format` flag (out of scope).
- `output/console.py` não será criado — CLI já faz o render via `rich.Markdown`.
- Sem streaming da resposta do LLM (complexidade desnecessária para agora).
