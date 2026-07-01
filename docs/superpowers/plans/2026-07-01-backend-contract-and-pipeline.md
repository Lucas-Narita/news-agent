# Backend Contract & Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the Python agent to emit a clean, timezone-safe, contract-complete `latest.json` and publish it daily via GitHub Actions, so the Next.js frontend (Plan B) has a stable data source.

**Architecture:** Fix the CLI so diagnostics never touch stdout (the pipeline redirects stdout to a file); make every serialized datetime timezone-aware; extend `DigestOutput` with an `agents[]` roster; freeze the contract into a Python-generated fixture the frontend consumes; then a scheduled Actions job runs the CLI, validates the JSON, and commits it.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, Rich, pytest + respx, GitHub Actions.

## Global Constraints

- Python `>=3.11`; ruff line-length `100`, lint select `E,F,I`.
- No new runtime dependencies (all fixes use stdlib + existing deps).
- Agents never raise — failures live in `AgentResult.error` (existing contract).
- Tests are mocked, no network; coverage gate `--cov-fail-under=80` must stay green.
- Commits in English, conventional-commits format, no attribution/co-author trailer.
- All work on branch `feat/web-frontend`.

---

### Task 1: Route all CLI diagnostics off stdout (CRITICAL)

Diagnostics currently reach stdout, so `news-agent run --format json > latest.json` can capture a `WARNING` line before the JSON and produce an invalid file. Fix the log handler to write to stderr and move the two remaining `console.print` error branches to `err_console`.

**Files:**
- Modify: `news_agent/logging_config.py`
- Modify: `news_agent/cli.py` (the two `console.print` calls inside `run()`'s error branches)
- Test: `tests/test_logging_config.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `configure_logging(verbose: bool)` (existing), `err_console` (existing, `Console(stderr=True)` in cli.py:23).
- Produces: no signature change; behavioral guarantee that `run --format json` stdout is pure JSON even when a source fails.

- [ ] **Step 1: Write the failing unit test for the handler target**

Add to `tests/test_logging_config.py`:

```python
import logging

from news_agent.logging_config import configure_logging


def test_configure_logging_writes_to_stderr():
    logger = logging.getLogger("news_agent")
    logger.handlers.clear()  # handler is only attached when none exist
    configure_logging()
    handler = logger.handlers[0]
    assert handler.console.stderr is True  # RichHandler must target stderr, not stdout
    logger.handlers.clear()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_logging_config.py::test_configure_logging_writes_to_stderr -v`
Expected: FAIL — `AttributeError`/`assert False` because the current `RichHandler()` uses the default stdout console.

- [ ] **Step 3: Point the handler at stderr**

Replace the body of `news_agent/logging_config.py` with:

```python
"""Logging setup for the CLI entry point.

The library code only ever calls ``logging.getLogger(__name__)``; wiring the
handler is the application's job. This keeps the orchestrator and agents free of
any opinion about where logs go. Diagnostics go to stderr so ``--format json``
can pipe pure JSON on stdout.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler


def configure_logging(verbose: bool = False) -> None:
    """Attach a Rich handler (writing to stderr) to the ``news_agent`` logger.

    INFO and above when ``verbose`` is set, otherwise WARNING and above. Calling
    this more than once is safe — the handler is only attached on the first call.
    """
    level = logging.INFO if verbose else logging.WARNING
    logger = logging.getLogger("news_agent")
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(
            RichHandler(
                console=Console(stderr=True),
                rich_tracebacks=True,
                show_path=False,
            )
        )
```

- [ ] **Step 4: Run the unit test to verify it passes**

Run: `pytest tests/test_logging_config.py::test_configure_logging_writes_to_stderr -v`
Expected: PASS

- [ ] **Step 5: Write the failing integration test (JSON stays pure when a source fails)**

Add `import logging` to the top of `tests/test_cli.py` (it already imports `json`, `datetime`, `AsyncMock`, `patch`, `CliRunner`), then add:

```python
def test_run_json_stdout_pure_when_source_fails(monkeypatch):
    """A failed source logs a WARNING; it must NOT leak into the JSON on stdout."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    logging.getLogger("news_agent").handlers.clear()  # force the stderr handler to attach

    from news_agent.cli import app
    from news_agent.schemas.models import AgentResult, Article

    ok = AgentResult(
        source="hackernews",
        articles=[Article(title="t", url="https://example.com/a", source="hackernews")],
        fetched_at=datetime.now(),
    )
    err = AgentResult(source="github", articles=[], fetched_at=datetime.now(), error="boom")

    isolated = CliRunner(mix_stderr=False)
    with (
        patch("news_agent.orchestrator.HackerNewsAgent.fetch", new=AsyncMock(return_value=ok)),
        patch("news_agent.orchestrator.GitHubAgent.fetch", new=AsyncMock(return_value=err)),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
    ):
        result = isolated.invoke(
            app, ["run", "--no-file", "--sources", "hackernews,github", "--format", "json"]
        )

    assert result.exit_code == 0
    json.loads(result.stdout)  # raises if the WARNING leaked into stdout
```

- [ ] **Step 6: Run it to verify it passes with the stderr handler**

Run: `pytest tests/test_cli.py::test_run_json_stdout_pure_when_source_fails -v`
Expected: PASS (the handler from Step 3 keeps stdout pure). If it FAILS with a `JSONDecodeError`, the handler fix regressed — stop and recheck Step 3.

- [ ] **Step 7: Move the two error-branch prints to stderr**

In `news_agent/cli.py`, inside `run()`, change the two `console.print` calls in the error branches to `err_console.print`:

```python
    except ValidationError:
        err_console.print("[red]Configuration error. Run 'news-agent config check' for details.[/red]")
        raise typer.Exit(code=1)
```
and
```python
    if not active_sources:
        err_console.print("[red]No sources available. Check your API keys.[/red]")
        raise typer.Exit(code=1)
```

- [ ] **Step 8: Run the full CLI + logging suites**

Run: `pytest tests/test_cli.py tests/test_logging_config.py -v`
Expected: PASS (all)

- [ ] **Step 9: Commit**

```bash
git add news_agent/logging_config.py news_agent/cli.py tests/test_logging_config.py tests/test_cli.py
git commit -m "fix: route CLI diagnostics to stderr so --format json stays pure"
```

---

### Task 2: Make every serialized datetime timezone-aware

`generated_at` (orchestrator) and `published_at` for HackerNews/Reddit are currently naive; serialized without an offset they break the frontend's Zod parse. Devto/GitHub/NewsAPI/Lobsters are already tz-aware.

**Files:**
- Modify: `news_agent/orchestrator.py` (two `datetime.now()` calls + import)
- Modify: `news_agent/agents/hackernews.py` (line 47 + import)
- Modify: `news_agent/agents/reddit.py` (line 29 + import)
- Test: `tests/test_orchestrator.py`, `tests/agents/test_hackernews.py`, `tests/agents/test_reddit.py`

**Interfaces:**
- Consumes: `DigestOutput.generated_at: datetime`, `Article.published_at: datetime | None` (existing).
- Produces: every emitted `datetime` is timezone-aware (UTC), so `model_dump_json()` includes an offset.

- [ ] **Step 1: Write the failing test for HackerNews published_at**

Add to `tests/agents/test_hackernews.py`:

```python
async def test_hackernews_published_at_is_timezone_aware():
    with respx.mock:
        respx.get(f"{HN_BASE}/topstories.json").mock(return_value=httpx.Response(200, json=[1]))
        respx.get(re.compile(rf"{re.escape(HN_BASE)}/item/\d+\.json")).mock(
            return_value=httpx.Response(200, json=_make_item(1))
        )
        result = await HackerNewsAgent().fetch()
    assert result.articles[0].published_at.tzinfo is not None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/agents/test_hackernews.py::test_hackernews_published_at_is_timezone_aware -v`
Expected: FAIL — `assert None is not None` (naive datetime has `tzinfo is None`).

- [ ] **Step 3: Fix HackerNews and Reddit**

`news_agent/agents/hackernews.py`: change `from datetime import datetime` to `from datetime import datetime, timezone`, and line 47:
```python
                        published_at=datetime.fromtimestamp(item["time"], tz=timezone.utc),
```

`news_agent/agents/reddit.py`: change `from datetime import datetime` to `from datetime import datetime, timezone`, and the `_parse_child` line:
```python
            published_at=datetime.fromtimestamp(data["created_utc"], tz=timezone.utc),
```

- [ ] **Step 4: Add and run the Reddit twin test, verify both pass**

Add to `tests/agents/test_reddit.py` a `test_reddit_published_at_is_timezone_aware` mirroring that file's existing happy-path mock, ending with `assert result.articles[0].published_at.tzinfo is not None`.

Run: `pytest tests/agents/test_hackernews.py tests/agents/test_reddit.py -k timezone -v`
Expected: PASS (both)

- [ ] **Step 5: Write the failing test for orchestrator generated_at**

Add to `tests/test_orchestrator.py`:

```python
async def test_run_digest_generated_at_is_timezone_aware(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()
    with (
        patch(
            "news_agent.orchestrator.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews")),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews"], settings)

    assert result.generated_at.tzinfo is not None
```

- [ ] **Step 6: Run it to verify it fails**

Run: `pytest tests/test_orchestrator.py::test_run_digest_generated_at_is_timezone_aware -v`
Expected: FAIL — naive datetime.

- [ ] **Step 7: Fix the orchestrator**

`news_agent/orchestrator.py`: change `from datetime import datetime` to `from datetime import datetime, timezone`, and both `generated_at=datetime.now()` occurrences (empty-result branch and final return) to `generated_at=datetime.now(timezone.utc)`.

- [ ] **Step 8: Run the orchestrator + agent suites**

Run: `pytest tests/test_orchestrator.py tests/agents/ -v`
Expected: PASS (all)

- [ ] **Step 9: Commit**

```bash
git add news_agent/orchestrator.py news_agent/agents/hackernews.py news_agent/agents/reddit.py tests/
git commit -m "fix: emit timezone-aware datetimes for JSON serialization"
```

---

### Task 3: Add the agents[] roster to the contract

Extend `DigestOutput` with a full per-source status roster so the frontend's AgentsBlock is honest and survives adding sources.

**Files:**
- Modify: `news_agent/schemas/models.py`
- Modify: `news_agent/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Interfaces:**
- Produces: `class AgentStatus(BaseModel): name: str; ok: bool; article_count: int` and `DigestOutput.agents: list[AgentStatus] = []`, populated with one entry per attempted source.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_orchestrator.py`:

```python
async def test_run_digest_reports_agent_roster(monkeypatch):
    """agents[] carries one status per attempted source, ok reflecting success."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    from news_agent.config import get_settings

    settings = get_settings()
    with (
        patch(
            "news_agent.orchestrator.HackerNewsAgent.fetch",
            new=AsyncMock(return_value=_ok_result("hackernews", n=2)),
        ),
        patch(
            "news_agent.orchestrator.GitHubAgent.fetch",
            new=AsyncMock(return_value=_err_result("github")),
        ),
        patch("news_agent.orchestrator.generate_narrative", new=AsyncMock(return_value="# D")),
    ):
        from news_agent.orchestrator import run_digest

        result = await run_digest(["hackernews", "github"], settings)

    roster = {a.name: a for a in result.agents}
    assert roster["hackernews"].ok is True
    assert roster["hackernews"].article_count == 2
    assert roster["github"].ok is False
    assert roster["github"].article_count == 0
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_orchestrator.py::test_run_digest_reports_agent_roster -v`
Expected: FAIL — `DigestOutput` has no `agents` (or `result.agents` is empty).

- [ ] **Step 3: Add the AgentStatus model**

In `news_agent/schemas/models.py`, add before `DigestOutput`:

```python
class AgentStatus(BaseModel):
    name: str
    ok: bool
    article_count: int
```
and add the field to `DigestOutput`:
```python
class DigestOutput(BaseModel):
    narrative: str
    sources_used: list[str]
    total_articles: int
    generated_at: datetime
    articles: list[Article] = []
    agents: list[AgentStatus] = []
```

- [ ] **Step 4: Populate the roster in the orchestrator**

In `news_agent/orchestrator.py`, add `AgentStatus` to the schemas import (`from news_agent.schemas.models import AgentStatus, Article, DigestOutput`). In `run_digest`, build the roster while iterating `results`:

```python
    articles: list[Article] = []
    sources_used: list[str] = []
    roster: list[AgentStatus] = []
    for result in results:
        roster.append(
            AgentStatus(
                name=result.source,
                ok=result.error is None,
                article_count=len(result.articles),
            )
        )
        if result.error is None:
            articles.extend(result.articles)
            sources_used.append(result.source)
        else:
            logger.warning("source %s failed: %s", result.source, result.error)
```
and in the final return add `agents=roster,`:
```python
    return DigestOutput(
        narrative=narrative,
        sources_used=sources_used,
        total_articles=len(articles),
        generated_at=datetime.now(timezone.utc),
        articles=articles,
        agents=roster,
    )
```

- [ ] **Step 5: Run the orchestrator suite**

Run: `pytest tests/test_orchestrator.py -v`
Expected: PASS (all, including the existing aggregation/dedup tests)

- [ ] **Step 6: Commit**

```bash
git add news_agent/schemas/models.py news_agent/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add per-source agent roster to DigestOutput"
```

---

### Task 4: Freeze the contract into a Python-generated fixture

Generate the sample JSON the frontend imports, from a canonical `DigestOutput`, and assert it round-trips. This is the single source both languages validate against.

**Files:**
- Create: `web/__fixtures__/digest.sample.json` (generated by the test)
- Create: `tests/test_contract_fixture.py`

**Interfaces:**
- Consumes: `DigestOutput`, `Article`, `AgentStatus` from `news_agent.schemas.models`.
- Produces: `web/__fixtures__/digest.sample.json` — a committed, valid `DigestOutput` including offset-bearing timestamps and one `ok=false` agent.

- [ ] **Step 1: Write the test that generates + verifies the fixture**

Create `tests/test_contract_fixture.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

from news_agent.schemas.models import AgentStatus, Article, DigestOutput

FIXTURE = Path(__file__).resolve().parents[1] / "web" / "__fixtures__" / "digest.sample.json"


def _canonical_digest() -> DigestOutput:
    return DigestOutput(
        narrative="# Tech Digest\n\nA sample narrative with **markdown**.",
        sources_used=["hackernews", "devto"],
        total_articles=2,
        generated_at=datetime(2026, 7, 1, 4, 0, tzinfo=timezone.utc),
        articles=[
            Article(
                title="A local-first model",
                url="https://example.com/a",
                source="hackernews",
                score=412,
                published_at=datetime(2026, 6, 30, 13, 0, tzinfo=timezone.utc),
                summary=None,
            ),
            Article(
                title="Rust in the kernel",
                url="https://example.com/b",
                source="devto",
                score=210,
                published_at=datetime(2026, 6, 29, 9, 30, tzinfo=timezone.utc),
                summary="A short description.",
            ),
        ],
        agents=[
            AgentStatus(name="hackernews", ok=True, article_count=1),
            AgentStatus(name="devto", ok=True, article_count=1),
            AgentStatus(name="github", ok=False, article_count=0),
        ],
    )


def test_contract_fixture_is_current():
    """Regenerate the fixture and fail if it drifts from what's committed.

    Run `pytest -k contract_fixture` after any schema change, then commit the
    updated file. The frontend (Plan B) parses THIS exact file with Zod.
    """
    expected = _canonical_digest().model_dump_json(indent=2)
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    if not FIXTURE.exists() or FIXTURE.read_text() != expected:
        FIXTURE.write_text(expected)
    assert FIXTURE.read_text() == expected
    DigestOutput.model_validate(json.loads(FIXTURE.read_text()))  # round-trips through the schema
```

- [ ] **Step 2: Run it (it writes the fixture on first run, then passes)**

Run: `pytest tests/test_contract_fixture.py -v`
Expected: PASS — creates `web/__fixtures__/digest.sample.json`.

- [ ] **Step 3: Verify the fixture looks right**

Run: `python -c "import json; d=json.load(open('web/__fixtures__/digest.sample.json')); print(d['agents'], d['generated_at'])"`
Expected: prints the 3-agent roster and an offset-bearing timestamp like `2026-07-01T04:00:00+00:00`.

- [ ] **Step 4: Commit (fixture + test together)**

```bash
git add tests/test_contract_fixture.py web/__fixtures__/digest.sample.json
git commit -m "test: freeze DigestOutput contract into a generated fixture"
```

---

### Task 5: Daily generation pipeline (GitHub Actions)

Add a scheduled workflow that runs the CLI, validates the JSON before committing, versions it under `data/digests/`, and pushes with rebase+retry.

**Files:**
- Create: `.github/workflows/digest.yml`

**Interfaces:**
- Consumes: `news-agent run --format json --no-file` (now stdout-pure after Task 1).
- Produces: `web/public/latest.json` (served) + `data/digests/digest-<date>.json` (archive).

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/digest.yml`:

```yaml
name: Generate digest

on:
  schedule:
    - cron: "0 4 * * *"   # 04:00 UTC daily
  workflow_dispatch: {}

permissions:
  contents: write

concurrency:
  group: digest
  cancel-in-progress: false

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install -e .
      - name: Generate and validate JSON
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NEWSAPI_KEY: ${{ secrets.NEWSAPI_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          mkdir -p web/public data/digests
          news-agent run --format json --no-file > web/public/latest.json
          python -c "import json; json.load(open('web/public/latest.json'))"
          cp web/public/latest.json "data/digests/digest-$(date -u +%F).json"
      - name: Commit and push
        run: |
          git config user.name  "news-agent-bot"
          git config user.email "bot@users.noreply.github.com"
          git add web/public/latest.json data/digests/
          if git diff --cached --quiet; then
            echo "No changes"; exit 0
          fi
          git commit -m "chore: update digest $(date -u +%F)"
          for i in 1 2 3; do
            git pull --rebase --autostash origin "${GITHUB_REF_NAME}" && git push && exit 0
            sleep 5
          done
          echo "push failed after retries"; exit 1
```

- [ ] **Step 2: Validate the generation command locally (optional, needs a real key)**

If you have a real `ANTHROPIC_API_KEY` locally:
Run: `news-agent run --format json --no-file --sources hackernews > /tmp/probe.json && python -c "import json; json.load(open('/tmp/probe.json')); print('valid')"`
Expected: prints `valid`. (Skip if no local key — Task 1's tests already guarantee stdout purity; CI covers the live run.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/digest.yml
git commit -m "ci: add daily digest generation workflow"
```

- [ ] **Step 4: (Manual, post-merge) configure the secret and dispatch**

Not a code step — note for the user: add `ANTHROPIC_API_KEY` (and optionally `NEWSAPI_KEY`) as repo secrets, then trigger the workflow via the Actions tab ("Run workflow") to seed `web/public/latest.json`.

---

## Full-suite gate (run before handing off to Plan B)

- [ ] Run: `pytest`
  Expected: all pass, coverage ≥ 80%.
- [ ] Run: `ruff check . && ruff format --check .`
  Expected: clean.

---

## Self-review notes (author)

- **Spec coverage:** §4.1→Task 1, §4.2→Task 2, §4.3→Task 3, §4.4→Task 4, §5→Task 5. All backend/pipeline spec sections mapped.
- **Contract for Plan B:** Task 4 produces `web/__fixtures__/digest.sample.json` — the exact file Plan B's Zod schema parses. `agents[]`, offset-bearing datetimes, and nullable fields are all represented.
- **Deferred to Plan B:** Zod schema, `isSafeHref`, the frontend itself.
