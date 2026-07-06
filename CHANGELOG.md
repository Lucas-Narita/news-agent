# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- arXiv agent (`arxiv`) surfacing recent cs.AI papers — no API key required.

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
