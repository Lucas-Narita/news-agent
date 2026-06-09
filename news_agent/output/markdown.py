from news_agent.schemas.models import Article


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

    sections = []
    for source, items in by_source.items():
        lines = [f"## {source.capitalize()}"]
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
