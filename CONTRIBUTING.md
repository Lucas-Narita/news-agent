# Contributing

This is primarily a portfolio project, but issues and pull requests are welcome.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Before opening a PR

```bash
ruff check .
ruff format --check .
pytest
```

The test suite is fully mocked (`respx` for HTTP, `unittest.mock` for the LLM) — no network
access or API keys are required to run it. Coverage is gated at 80% (`pyproject.toml`).

## Conventions

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, ...).
- Adding a news source means creating one `BaseAgent` subclass in `news_agent/agents/` and
  registering it — the orchestrator itself never changes.
- Pydantic models in `news_agent/schemas/` are the contract between agents and the rest of the
  pipeline; validate at the boundary rather than trusting raw dicts deeper in the code.
