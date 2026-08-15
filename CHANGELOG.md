# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- arXiv agent (`arxiv`) surfacing recent cs.AI papers — no API key required.
- `news-agent sources` command listing every registered source and whether it is usable.
- `--output-dir` flag overriding the configured output directory for a single run.
- Configurable `CACHE_TTL`, `ANTHROPIC_MODEL`, `MAX_TOKENS` and `ARXIV_CATEGORY` settings.
- Per-agent fetch timing and article counts under `--verbose`, plus retry and cache-hit logs.
- Unavailable sources are now named in the terminal output instead of silently missing.

### Changed

- Deduplication matches on a canonical URL (tracking parameters and trailing slash stripped),
  so the same story shared across sources collapses into one entry.
- Ranking ties break by recency then URL, and digest sections render in declared source order,
  making the generated Markdown byte-identical for the same input.
- Source names render as their communities spell them (`Hacker News`, `Dev.to`, `arXiv`).
- The digest filename now follows the digest's own UTC timestamp rather than local wall time.
- The Claude call is retried on transient failures, like every source already was.
- The prompt's Highlights sections are generated from the source list, so a new agent cannot be
  left without a section.
- Ruff now enforces `UP`, `C4`, `SIM` and `B` in addition to `E`, `F` and `I`.

### Fixed

- Malformed items from Hacker News, GitHub and NewsAPI are skipped individually instead of
  failing the whole source.
- The Lobsters agent is capped at 10 results, matching every other source.
- `REQUEST_TIMEOUT=0` and `--limit 0` are rejected instead of silently producing an empty digest.
- A typo in `--sources` is reported instead of being dropped in silence.
- Every text block in a multi-block Claude response is kept; only the first was returned before.
- The digest cache is written atomically, so an interrupted run cannot leave a corrupt file.

## [0.1.0]

### Added

- Multi-agent orchestrator (`asyncio.gather`) aggregating six sources: Hacker News, GitHub
  Trending, NewsAPI, Reddit, Dev.to, and Lobsters.
- `BaseAgent` contract with graceful degradation — a failing source degrades the digest instead
  of breaking the run (`AgentResult.error`).
- Claude-generated Markdown narrative with prompt caching for the fixed system prompt.
- CLI (`Typer`) with `--sources`, `--limit`, `--verbose`, `--format json`, and `config check`.
- Deduplication by URL and score-based ranking before the LLM narrates.
- Generic async retry with exponential backoff for transient HTTP failures.
- Configurable request timeout and structured logging (`--verbose`).
- Static Next.js web frontend that prerenders the daily digest, deployed free on Vercel.
- Scheduled GitHub Action that regenerates the digest and commits `latest.json` daily.
- Test suite (`pytest` + `respx`, fully mocked) with an 80% coverage gate in CI.
- GitHub Actions CI across Python 3.11, 3.12, and 3.13 (lint, format check, tests).
