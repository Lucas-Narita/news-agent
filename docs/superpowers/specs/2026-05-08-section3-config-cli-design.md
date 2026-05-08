# Section 3 Design — Config + CLI

**Project:** news-agent  
**Date:** 2026-05-08  
**Status:** Approved  

---

## Scope

This spec covers three files:

- `pyproject.toml` — packaging, dependencies, entry point
- `news_agent/config.py` — pydantic-settings configuration
- `news_agent/cli.py` — Typer CLI with nested subcommands

---

## pyproject.toml

Entry point: `news-agent = "news_agent.cli:app"`

**Runtime dependencies:**

| Package | Purpose |
|---|---|
| `typer[all]` | CLI framework + rich integration |
| `pydantic>=2` | Schema validation (decided in Section 2) |
| `pydantic-settings` | Env-based configuration |
| `anthropic` | Claude API client |
| `httpx` | Async HTTP for agents |
| `rich` | Terminal formatting |

**Dev dependencies:** `pytest`, `pytest-asyncio`, `ruff`

Python requirement: `>=3.11`

No `requirements.txt`, no `setup.py`. `pyproject.toml` is the single source of truth.

---

## config.py

Uses `pydantic-settings`. The `Settings` class reads all values from environment variables or `.env`. Missing required fields raise a clear validation error at startup — before any network call.

```python
class Settings(BaseSettings):
    # Required
    anthropic_api_key: str

    # Optional — absence triggers graceful auto-detect skip
    newsapi_key: str | None = None
    github_token: str | None = None

    # Output
    output_dir: Path = Path("./output")

    # Default sources (overridable via --sources flag)
    default_sources: list[str] = ["hackernews", "github", "newsapi"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

**Singleton pattern:** `get_settings()` with `@lru_cache` — loaded once, reused throughout. Easy to override in tests via `get_settings.cache_clear()`.

**Auto-detect rule:** if `newsapi_key is None`, the `NewsAPIAgent` is marked inactive before `asyncio.gather()`. The agent returns `AgentResult(error="NEWSAPI_KEY not configured")`. The orchestrator does not need to know — graceful degradation is the agent's responsibility, consistent with the Section 2 architecture contract.

---

## cli.py

Two Typer instances: `app` (root) and `config_app` (sub-app for the `config` group).  
`config_app` is registered via `app.add_typer(config_app, name="config")`.

### Commands

```
news-agent run
  --sources TEXT    Comma-separated source names: hackernews, github, newsapi (default: all configured)
  --no-file         Print digest to terminal only, skip writing .md file

news-agent config check
                    Validate env vars and display status of each key
```

### `run` behavior

1. Load `Settings` — fails fast if `ANTHROPIC_API_KEY` is absent
2. Resolve sources: `--sources` overrides `settings.default_sources`; auto-detect removes sources without a configured key
3. Display rich startup panel (active sources, timestamp)
4. Call `asyncio.run(orchestrator.run())` 
5. Display digest in terminal; write `.md` to `output/` unless `--no-file`

### `config check` behavior

Displays a rich table with each variable, its status (`OK` / `MISSING` / `OPTIONAL`), and whether it is configured. Makes no network calls — inspects `Settings` only. Useful for onboarding and live demos.

### Error handling

All unhandled exceptions are caught at the CLI boundary, displayed as `rich` error messages, and converted to `typer.Exit(code=1)`. No raw tracebacks are shown to the end user.

---

## Decisions not made in this section

- Orchestrator internals (Section 5)
- LLM prompt strategy (Section 6)
- Rich output formatting details (Section 7)

---

## Open questions

None — all design decisions resolved.
