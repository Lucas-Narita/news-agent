# news-agent

[![CI](https://github.com/Lucas-Narita/news-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Lucas-Narita/news-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

A multi-agent CLI that aggregates tech news from **HackerNews**, **GitHub Trending**, and
**NewsAPI** in parallel, then uses **Claude** to turn the raw feed into a concise Markdown
digest — printed to the terminal and saved to disk.

> Built as a focused demonstration of agent-oriented architecture: independent agents behind a
> shared contract, real `asyncio` parallelism, graceful degradation, and an LLM used only where
> natural language is actually needed.

---

## Why this design

| Decision | Rationale |
|---|---|
| **Multi-agent over a linear script** | Each source has its own rate limit, latency, and payload shape. Running them with `asyncio.gather` cuts wall-clock from ~9s (3×3s serial) to ~3s. The `BaseAgent` contract means a new source is *one new file + one registry line* — the orchestrator never changes (Open/Closed). |
| **Pydantic at every boundary** | Validation happens where data enters the system. If an upstream API changes shape, the failure surfaces as a clear `AgentResult.error`, not a silent `KeyError` deep in the pipeline. |
| **Errors as data (`AgentResult.error`)** | Agents never raise. The orchestrator doesn't need to know *how* each API fails — it just skips sources with an error. One dead API degrades the digest instead of breaking the run. |
| **LLM only on the narrative step** | Fetch, normalize, and filter are deterministic code. Claude is called once, at the end, where language generation is the actual requirement. Cheaper, and the whole pipeline is testable without mocking an LLM. |
| **Prompt caching** | The large, fixed system prompt is sent as a cached (`ephemeral`) block, so repeated runs only pay for the small, varying user message. |

---

## Architecture

```
CLI (Typer)
 └─► Orchestrator
       ├─► HackerNewsAgent  ─┐
       ├─► GitHubAgent       ├─► asyncio.gather() → AgentResult[]
       └─► NewsAPIAgent     ─┘
             │
             ▼
        LLM Client (Claude API · claude-sonnet-4-6, prompt caching)
             │
             ▼
     console (rich Markdown) + output/digest-YYYY-MM-DD-HH.md
```

Each agent implements a single method:

```python
class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AgentResult:
        """Fetch and normalize data. Never raises exceptions."""
```

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

Sources auto-disable when their key is missing: no `NEWSAPI_KEY` simply drops the `newsapi`
source instead of erroring.

---

## Usage

```bash
# Digest from all available sources
news-agent run

# Pick specific sources
news-agent run --sources hackernews,github

# Print to terminal only, skip writing the .md file
news-agent run --no-file

# Inspect configuration status
news-agent config check
```

Digests are written to `output/digest-YYYY-MM-DD-HH.md` by default.

---

## Project layout

```
news_agent/
├── cli.py            # Typer entry point
├── config.py         # pydantic-settings (typed env)
├── orchestrator.py   # asyncio.gather + graceful degradation
├── agents/           # BaseAgent ABC + hackernews / github / newsapi
├── schemas/          # Article, AgentResult, DigestOutput
├── llm/              # Claude client + prompt templates
└── output/           # Markdown formatter + rich console renderer
```

---

## Testing

The suite is fully mocked (`respx` for HTTP, `unittest.mock` for the LLM) — no network and no
API keys required.

```bash
pytest tests/
```
