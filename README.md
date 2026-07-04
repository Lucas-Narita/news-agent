# news-agent

[![CI](https://github.com/Lucas-Narita/news-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Lucas-Narita/news-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

A multi-agent CLI that aggregates tech news from **Hacker News**, **GitHub Trending**,
**NewsAPI**, **Reddit**, **Dev.to**, and **Lobsters** in parallel, then uses **Claude** to turn
the raw feed into a concise digest — rendered in the terminal, saved to disk, or emitted as JSON.

> Built as a focused demonstration of agent-oriented architecture: independent agents behind a
> shared contract, real `asyncio` parallelism, graceful degradation, retry with backoff, and an
> LLM used only where natural language is actually needed.

---

## Why this design

| Decision | Rationale |
|---|---|
| **Multi-agent over a linear script** | Each source has its own rate limit, latency, and payload shape. Running them with `asyncio.gather` keeps wall-clock close to the *slowest* source rather than their sum. The `BaseAgent` contract means a new source is *one new file + one registry line* — the orchestrator never changes (Open/Closed). |
| **Pydantic at every boundary** | Validation happens where data enters the system. If an upstream API changes shape, the failure surfaces as a clear `AgentResult.error`, not a silent `KeyError` deep in the pipeline. |
| **Errors as data (`AgentResult.error`)** | Agents never raise. The orchestrator doesn't need to know *how* each API fails — it just skips sources with an error and logs it. One dead API degrades the digest instead of breaking the run. |
| **Retry with exponential backoff** | A generic `with_retry` helper wraps every source's main request, so a transient timeout or 5xx is retried instead of costing the whole source. |
| **Dedupe + rank before the LLM** | The same story surfaces on several sources; duplicates are collapsed by URL (keeping the highest-scored copy) and the survivors are ranked by score. The LLM only ever sees a clean, prioritized list — which also trims token cost. |
| **LLM only on the narrative step** | Fetch, normalize, dedupe, and rank are deterministic code. Claude is called once, at the end, where language generation is the actual requirement. Cheaper, and the whole pipeline is testable without mocking an LLM. |
| **Prompt caching** | The large, fixed system prompt is sent as a cached (`ephemeral`) block, so repeated runs only pay for the small, varying user message. |

---
## oi
## Architecture

```
CLI (Typer)
 └─► Orchestrator
       ├─► HackerNewsAgent  ─┐
       ├─► GitHubAgent       │
       ├─► NewsAPIAgent      ├─► asyncio.gather() → AgentResult[]
       ├─► RedditAgent       │        │
       ├─► DevToAgent        │        ▼
       └─► LobstersAgent    ─┘   dedupe + rank (processing.py)
                                      │
                                      ▼
                          LLM Client (Claude · prompt caching)
                                      │
                                      ▼
            console (rich) · digest-*.md · digest-*.json (--format json)
```

Each agent implements a single method and reuses the shared `with_retry` helper:

```python
class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AgentResult:
        """Fetch and normalize data. Never raises exceptions."""
```

---

## Web frontend & daily digest

The digest also ships as a **static web page**. A scheduled GitHub Action runs the CLI in JSON mode,
and a [Next.js 16](web/) frontend prerenders that JSON at build time — no server, no runtime LLM
calls, nothing to pay for.

```
digest.yml (daily · GitHub Actions)              web/ (Next.js 16 · static)
    news-agent run --format json                     prerender from latest.json
             │                                                  ▲
             └──►  web/public/latest.json (committed) ──────────┘
                             │
                             └──►  Vercel rebuild on each commit  ──►  CDN
```

- **Static by design** — the page builds to `○ (Static)`, a plain CDN document, so it stays free and
  has no cold starts.
- **One contract across the stack** — the frontend validates `latest.json` against a zod schema that
  mirrors the backend `DigestOutput` Pydantic model, and a drift fixture test freezes that contract.
- **Free daily refresh** — each Action commit to `latest.json` triggers a fresh Vercel build, so the
  page updates without a server.

Frontend details: [`web/README.md`](web/README.md). Deploy steps (including the required
Root Directory = `web`): [`DEPLOY.md`](DEPLOY.md).

---

## Setup

Requires **Python 3.11+** and an [Anthropic API key](https://console.anthropic.com/).

```bash
# Create a virtualenv and install in editable mode with dev dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Copy and fill in your keys
cp .env.example .env
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Claude API key — powers the digest narrative |
| `NEWSAPI_KEY` | No | [NewsAPI](https://newsapi.org/) key — enables the `newsapi` source |
| `GITHUB_TOKEN` | No | GitHub token — raises the rate limit from 60 to 5000 req/h |
| `REQUEST_TIMEOUT` | No | Per-request HTTP timeout in seconds (default `10`) |

Hacker News, Reddit, Dev.to, and Lobsters need no credentials. `newsapi` auto-disables when its
key is missing instead of erroring.

---

## Usage

```bash
# Digest from all available sources
news-agent run

# Pick specific sources
news-agent run --sources hackernews,reddit,lobsters

# Keep only the top 5 ranked stories
news-agent run --limit 5

# Show what's happening under the hood (INFO logs to stderr)
news-agent run --verbose

# Emit machine-readable JSON (stdout stays clean, so it pipes into jq)
news-agent run --format json --no-file | jq '.articles[].url'

# Inspect configuration status
news-agent config check
```

Digests are written to `output/digest-YYYY-MM-DD-HH.{md,json}` by default. Progress messages go to
**stderr**, so `--format json` produces a clean JSON stream on **stdout**.

Exit code is `0` on success and `1` on configuration errors, no available sources, or an
unrecoverable fetch/generation failure — useful for scripting (`news-agent run || alert-me`).

---

## Project layout

```
news_agent/
├── cli.py             # Typer entry point (--sources, --limit, --verbose, --format)
├── config.py          # pydantic-settings (typed env, configurable timeout)
├── orchestrator.py    # asyncio.gather + dedupe/rank + graceful degradation
├── processing.py      # pure dedupe + ranking helpers
├── retry.py           # generic async retry with exponential backoff
├── logging_config.py  # Rich-handler logging setup
├── agents/            # BaseAgent ABC + 6 source agents
├── schemas/           # Article, AgentResult, DigestOutput
├── llm/               # Claude client + prompt templates
└── output/            # markdown / rich console / json renderers
```

---

## Testing

The suite is fully mocked (`respx` for HTTP, `unittest.mock` for the LLM, neutralized backoff) —
no network and no API keys required. Coverage is gated at 80% in `pyproject.toml`.

```bash
pytest
```
