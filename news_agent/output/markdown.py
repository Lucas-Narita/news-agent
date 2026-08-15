from news_agent.schemas.models import Article

# str.capitalize() mangles the names these communities actually use
# ("Hackernews", "Devto", "Arxiv"). The digest is read by humans and fed to the
# LLM as context, so both benefit from the real spelling.
SOURCE_LABELS = {
    "hackernews": "Hacker News",
    "github": "GitHub",
    "newsapi": "NewsAPI",
    "reddit": "Reddit",
    "devto": "Dev.to",
    "lobsters": "Lobsters",
    "arxiv": "arXiv",
}


_SECTION_ORDER = {name: index for index, name in enumerate(SOURCE_LABELS)}


def _section_rank(source: str) -> tuple[int, str]:
    """Sort key placing known sources in declared order, unknown ones last."""
    return (_SECTION_ORDER.get(source, len(_SECTION_ORDER)), source)


def source_label(source: str) -> str:
    """Human-facing name for a source, falling back to a capitalized slug."""
    return SOURCE_LABELS.get(source, source.capitalize())


def format_articles(articles: list[Article]) -> str:
    """Render a list of articles as a Markdown string grouped by source.

    Pure function — no I/O. Used both to build the LLM prompt context and as a
    deterministic fallback when no narrative is generated.
    """
    if not articles:
        return ""

    by_source: dict[str, list[Article]] = {}
    for article in articles:
        by_source.setdefault(article.source, []).append(article)

    # Sections follow the declared source order rather than whichever agent
    # happened to finish first, so two runs over the same articles produce a
    # byte-identical digest — which also keeps the LLM's context stable.
    ordered_sources = sorted(by_source, key=_section_rank)

    sections = []
    for source in ordered_sources:
        items = by_source[source]
        lines = [f"## {source_label(source)}"]
        for a in items:
            if source == "github" and a.score is not None:
                line = f"- **{a.title}** ★{a.score} — {a.url}"
            elif a.score is not None:
                line = f"- **{a.title}** (score: {a.score}) — {a.url}"
            else:
                line = f"- **{a.title}** — {a.url}"
            if a.summary:
                line += f"\n  {a.summary}"
            lines.append(line)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
