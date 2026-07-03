# Security Policy

This project is a portfolio/demo application with no user data storage or hosted service beyond
a static digest page — the practical attack surface is small, but reports are still welcome.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately via
[GitHub Security Advisories](https://github.com/Lucas-Narita/news-agent/security/advisories/new)
rather than a public issue. Include the affected file/endpoint and steps to reproduce.

## Scope Notes

- API keys (`ANTHROPIC_API_KEY`, `NEWSAPI_KEY`, `GITHUB_TOKEN`) are read from environment
  variables only; never commit a real `.env` file (see `.gitignore`).
- The web frontend (`web/`) is a static build with no server-side secrets or database.
