# Section 3: Config + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the news-agent project with packaging, pydantic-settings configuration, and a Typer CLI exposing `run` and `config check` commands.

**Architecture:** A `Settings` singleton (`pydantic-settings` + `lru_cache`) centralizes all configuration. The CLI has two commands: `run` orchestrates the full pipeline (with a stub until Section 5) and `config check` validates env vars without network calls. Source resolution lives in a pure `resolve_sources()` function for testability.

**Tech Stack:** Python 3.11+, Typer, pydantic-settings v2, rich, pytest, ruff

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Create | Package metadata, deps, entry point |
| `news_agent/__init__.py` | Create | Package marker |
| `news_agent/schemas/__init__.py` | Create | Package marker |
| `news_agent/agents/__init__.py` | Create | Package marker |
| `news_agent/llm/__init__.py` | Create | Package marker |
| `news_agent/output/__init__.py` | Create | Package marker |
| `news_agent/schemas/models.py` | Create | Article, AgentResult, DigestOutput |
| `news_agent/config.py` | Create | Settings class + get_settings() singleton |
| `news_agent/orchestrator.py` | Create | Stub for run_digest() — implemented in Section 5 |
| `news_agent/cli.py` | Create | Typer app: `run` + `config check` |
| `tests/__init__.py` | Create | Package marker |
| `tests/conftest.py` | Create | autouse fixture: cache clear + isolated env |
| `tests/test_schemas.py` | Create | Schema validation tests |
| `tests/test_config.py` | Create | Settings loading tests |
| `tests/test_cli.py` | Create | CLI command tests |
| `.env.example` | Create | Template for env vars |
| `.gitignore` | Create | Ignore .env, output/, __pycache__ |

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `news_agent/__init__.py`, `news_agent/schemas/__init__.py`, `news_agent/agents/__init__.py`, `news_agent/llm/__init__.py`, `news_agent/output/__init__.py`
- Create: `tests/__init__.py`
- Create: `.env.example`
- Create: `.gitignore`

No tests — pure scaffolding.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "news-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.12",
    "pydantic>=2",
    "pydantic-settings>=2",
    "anthropic>=0.28",
    "httpx>=0.27",
    "rich>=13",
]

[project.scripts]
news-agent = "news_agent.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]
```

- [ ] **Step 2: Create directory structure and package markers**

```bash
mkdir -p news_agent/agents news_agent/schemas news_agent/llm news_agent/output tests
touch news_agent/__init__.py \
      news_agent/agents/__init__.py \
      news_agent/schemas/__init__.py \
      news_agent/llm/__init__.py \
      news_agent/output/__init__.py \
      tests/__init__.py
```

- [ ] **Step 3: Create `.env.example`**

```
ANTHROPIC_API_KEY=your-anthropic-key-here
NEWSAPI_KEY=your-newsapi-key-here
GITHUB_TOKEN=your-github-token-here
OUTPUT_DIR=./output
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
output/
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
```

- [ ] **Step 5: Install the package in editable mode**

```bash
pip install -e ".[dev]"
```

Expected: no errors. `news-agent --help` will fail until `cli.py` exists — that's expected.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml news_agent/ tests/__init__.py .env.example .gitignore
git commit -m "chore: scaffold project structure and packaging"
```

---

## Task 2: Pydantic schemas (Section 2 data contracts)

**Files:**
- Create: `news_agent/schemas/models.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write failing tests**

`tests/test_schemas.py`:
```python
from datetime import datetime
import pytest
from pydantic import ValidationError
from news_agent.schemas.models import Article, AgentResult, DigestOutput


def test_article_requires_title_url_source():
    with pytest.raises(ValidationError):
        Article(url="https://example.com", source="hackernews")


def test_article_optional_fields_default_to_none():
    a = Article(title="Test", url="https://example.com", source="hackernews")
    assert a.score is None
    assert a.summary is None
    assert a.published_at is None


def test_agent_result_graceful_error():
    r = AgentResult(
        source="newsapi",
        articles=[],
        fetched_at=datetime.now(),
        error="NEWSAPI_KEY not configured",
    )
    assert r.error == "NEWSAPI_KEY not configured"
    assert r.articles == []


def test_agent_result_no_error_by_default():
    r = AgentResult(source="hackernews", articles=[], fetched_at=datetime.now())
    assert r.error is None


def test_digest_output():
    d = DigestOutput(
        narrative="Top stories this hour.",
        sources_used=["hackernews", "github"],
        total_articles=10,
        generated_at=datetime.now(),
    )
    assert d.total_articles == 10
    assert "hackernews" in d.sources_used
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_schemas.py -v
```

Expected: `ModuleNotFoundError: No module named 'news_agent.schemas.models'`

- [ ] **Step 3: Implement `news_agent/schemas/models.py`**

```python
from datetime import datetime
from pydantic import BaseModel


class Article(BaseModel):
    title: str
    url: str
    source: str
    score: int | None = None
    published_at: datetime | None = None
    summary: str | None = None


class AgentResult(BaseModel):
    source: str
    articles: list[Article]
    fetched_at: datetime
    error: str | None = None


class DigestOutput(BaseModel):
    narrative: str
    sources_used: list[str]
    total_articles: int
    generated_at: datetime
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_schemas.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add news_agent/schemas/models.py tests/test_schemas.py
git commit -m "feat: add pydantic schemas Article, AgentResult, DigestOutput"
```

---

## Task 3: Configuration (config.py)

**Files:**
- Create: `tests/conftest.py`
- Create: `news_agent/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create `tests/conftest.py`**

This fixture (a) clears the `get_settings` cache between tests and (b) changes the working directory to a temp path so no `.env` file in the project root is loaded during tests. `monkeypatch.setenv` is the only source of env vars in tests.

```python
import pytest
from news_agent.config import get_settings


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 2: Write failing tests**

`tests/test_config.py`:
```python
import pytest
from pathlib import Path
from pydantic import ValidationError
from news_agent.config import Settings, get_settings


def test_settings_requires_anthropic_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_reads_anthropic_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-test"


def test_optional_keys_default_to_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    s = Settings()
    assert s.newsapi_key is None
    assert s.github_token is None


def test_output_dir_defaults_to_output(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.output_dir == Path("output")


def test_output_dir_configurable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OUTPUT_DIR", "/tmp/digests")
    s = Settings()
    assert s.output_dir == Path("/tmp/digests")


def test_default_sources_all_three(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.default_sources == ["hackernews", "github", "newsapi"]


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'news_agent.config'`

- [ ] **Step 4: Implement `news_agent/config.py`**

```python
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    newsapi_key: str | None = None
    github_token: str | None = None
    output_dir: Path = Path("output")
    default_sources: list[str] = ["hackernews", "github", "newsapi"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add news_agent/config.py tests/conftest.py tests/test_config.py
git commit -m "feat: add pydantic-settings config with get_settings singleton"
```

---

## Task 4: CLI — `config check` command

**Files:**
- Create: `news_agent/cli.py` (partial — config_app only)
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cli.py`:
```python
import pytest
from typer.testing import CliRunner

runner = CliRunner()


def test_config_check_all_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1234")
    monkeypatch.setenv("NEWSAPI_KEY", "news-test-5678")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test-9012")
    from news_agent.cli import app
    result = runner.invoke(app, ["config", "check"])
    assert result.exit_code == 0
    assert "ANTHROPIC_API_KEY" in result.output
    assert "OK" in result.output


def test_config_check_optional_missing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-1234")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from news_agent.cli import app
    result = runner.invoke(app, ["config", "check"])
    assert result.exit_code == 0
    assert "OPTIONAL" in result.output


def test_config_check_missing_required(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from news_agent.cli import app
    result = runner.invoke(app, ["config", "check"])
    assert result.exit_code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'news_agent.cli'`

- [ ] **Step 3: Implement `news_agent/cli.py` (config check only)**

```python
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from news_agent.config import get_settings

app = typer.Typer(help="news-agent: tech news digest powered by Claude.")
config_app = typer.Typer(help="Configuration commands.")
app.add_typer(config_app, name="config")

console = Console()


@config_app.command("check")
def config_check():
    """Validate environment variables and display their status."""
    try:
        settings = get_settings()
    except ValidationError as e:
        console.print("[red]Configuration error:[/red]")
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            console.print(f"  [red]x[/red] {field}: {error['msg']}")
        raise typer.Exit(code=1)

    table = Table(title="Configuration Status")
    table.add_column("Variable", style="cyan")
    table.add_column("Status")
    table.add_column("Value")

    table.add_row(
        "ANTHROPIC_API_KEY",
        "[green]OK[/green]",
        "***" + settings.anthropic_api_key[-4:],
    )

    if settings.newsapi_key:
        table.add_row("NEWSAPI_KEY", "[green]OK[/green]", "***" + settings.newsapi_key[-4:])
    else:
        table.add_row("NEWSAPI_KEY", "[yellow]OPTIONAL[/yellow]", "not set")

    if settings.github_token:
        table.add_row("GITHUB_TOKEN", "[green]OK[/green]", "***" + settings.github_token[-4:])
    else:
        table.add_row("GITHUB_TOKEN", "[yellow]OPTIONAL[/yellow]", "not set")

    console.print(table)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: 3 passed

- [ ] **Step 5: Verify CLI manually**

```bash
ANTHROPIC_API_KEY=sk-test news-agent config check
```

Expected: rich table with `ANTHROPIC_API_KEY OK`, `NEWSAPI_KEY OPTIONAL`, `GITHUB_TOKEN OPTIONAL`.

- [ ] **Step 6: Commit**

```bash
git add news_agent/cli.py tests/test_cli.py
git commit -m "feat: add CLI with config check command"
```

---

## Task 5: CLI — `run` command + orchestrator stub

**Files:**
- Create: `news_agent/orchestrator.py`
- Modify: `news_agent/cli.py` (add `run` command and `resolve_sources`)
- Modify: `tests/test_cli.py` (add `run` tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_cli.py`:
```python
from unittest.mock import patch, AsyncMock
from datetime import datetime
from news_agent.schemas.models import DigestOutput


def _mock_digest() -> DigestOutput:
    return DigestOutput(
        narrative="Top stories this hour.",
        sources_used=["hackernews"],
        total_articles=3,
        generated_at=datetime.now(),
    )


def test_resolve_sources_from_flag(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.config import get_settings
    from news_agent.cli import resolve_sources
    settings = get_settings()
    assert resolve_sources("hackernews,github", settings) == ["hackernews", "github"]


def test_resolve_sources_auto_detects_missing_newsapi(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.config import get_settings
    from news_agent.cli import resolve_sources
    settings = get_settings()
    result = resolve_sources(None, settings)
    assert "newsapi" not in result
    assert "hackernews" in result
    assert "github" in result


def test_resolve_sources_includes_newsapi_when_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("NEWSAPI_KEY", "news-key")
    from news_agent.config import get_settings
    from news_agent.cli import resolve_sources
    settings = get_settings()
    result = resolve_sources(None, settings)
    assert "newsapi" in result


def test_run_no_file_prints_narrative(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app
    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(app, ["run", "--no-file", "--sources", "hackernews"])
    assert result.exit_code == 0
    assert "Top stories this hour." in result.output


def test_run_writes_md_file_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from news_agent.cli import app
    with patch("news_agent.cli.run_digest", new=AsyncMock(return_value=_mock_digest())):
        result = runner.invoke(app, ["run", "--sources", "hackernews"])
    assert result.exit_code == 0
    md_files = list(tmp_path.glob("digest-*.md"))
    assert len(md_files) == 1
    assert "Top stories this hour." in md_files[0].read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v -k "resolve_sources or test_run"
```

Expected: `ImportError: cannot import name 'resolve_sources' from 'news_agent.cli'`

- [ ] **Step 3: Create `news_agent/orchestrator.py` stub**

```python
from news_agent.config import Settings
from news_agent.schemas.models import DigestOutput


async def run_digest(sources: list[str], settings: Settings) -> DigestOutput:
    raise NotImplementedError("Implemented in Section 5")
```

- [ ] **Step 4: Add `resolve_sources` and `run` to `news_agent/cli.py`**

Add to the top of `news_agent/cli.py` (after existing imports):
```python
import asyncio
from datetime import datetime
from typing import Optional

from news_agent.config import Settings
from news_agent.orchestrator import run_digest
```

Add `resolve_sources` function (before the `@app.command()` decorator for `run`):
```python
def resolve_sources(sources_flag: Optional[str], settings: Settings) -> list[str]:
    """Return active sources after applying --sources flag and auto-detect."""
    if sources_flag:
        requested = [s.strip() for s in sources_flag.split(",")]
    else:
        requested = list(settings.default_sources)

    available = {
        "hackernews": True,
        "github": True,
        "newsapi": settings.newsapi_key is not None,
    }

    return [s for s in requested if available.get(s, False)]
```

Add `run` command at the end of `news_agent/cli.py`:
```python
@app.command()
def run(
    sources: Optional[str] = typer.Option(
        None, "--sources", help="Comma-separated: hackernews, github, newsapi"
    ),
    no_file: bool = typer.Option(False, "--no-file", help="Print to terminal only, skip .md file"),
):
    """Fetch tech news and generate a digest."""
    try:
        settings = get_settings()
    except ValidationError:
        console.print("[red]Configuration error. Run 'news-agent config check' for details.[/red]")
        raise typer.Exit(code=1)

    active_sources = resolve_sources(sources, settings)

    if not active_sources:
        console.print("[red]No sources available. Check your API keys.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Fetching from:[/bold] {', '.join(active_sources)}")

    try:
        digest = asyncio.run(run_digest(active_sources, settings))
    except NotImplementedError:
        console.print("[yellow]Orchestrator not yet implemented (Section 5).[/yellow]")
        raise typer.Exit(code=0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

    console.print(digest.narrative)

    if not no_file:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H")
        output_path = settings.output_dir / f"digest-{timestamp}.md"
        output_path.write_text(digest.narrative)
        console.print(f"[dim]Saved to {output_path}[/dim]")
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass (test_schemas: 5, test_config: 7, test_cli: 8 = 20 total)

- [ ] **Step 6: Verify CLI help output**

```bash
news-agent --help
news-agent run --help
news-agent config --help
news-agent config check --help
```

Expected: clean help text for every command and flag.

- [ ] **Step 7: Commit**

```bash
git add news_agent/cli.py news_agent/orchestrator.py tests/test_cli.py
git commit -m "feat: add run command with source resolution and orchestrator stub"
```

---

## Self-review

**Spec coverage:**
- `pyproject.toml` with entry point → Task 1 ✓
- `pydantic-settings` Settings singleton → Task 3 ✓
- `--sources` flag with auto-detect → Task 5 `resolve_sources` ✓
- `--no-file` flag → Task 5 `run` command ✓
- `config check` command → Task 4 ✓
- Graceful degradation via `AgentResult.error` → Task 2 schemas ✓
- No `.env` committed → Task 1 `.gitignore` ✓

**Placeholders:** none — all steps have complete code.

**Type consistency:**
- `run_digest(sources: list[str], settings: Settings) -> DigestOutput` — consistent between `orchestrator.py` stub and mock in `test_cli.py` ✓
- `resolve_sources(sources_flag: Optional[str], settings: Settings) -> list[str]` — consistent between implementation and tests ✓
- `Settings.newsapi_key: str | None` — checked as `is not None` in `resolve_sources` ✓
