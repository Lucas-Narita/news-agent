"""Prompt templates for the narrative step.

The Highlights sections are generated from ``SOURCE_GUIDANCE`` rather than
written out by hand: the prompt previously listed all seven sources twice, so
adding an agent meant remembering to edit prose in a second file or the new
source would silently never get a section. The rendered prompt is still a
module-level constant, so it stays byte-identical across runs and keeps
qualifying for Anthropic's prompt cache.
"""

from news_agent.output.markdown import source_label

# One entry per registered source, in the order sections should appear.
SOURCE_GUIDANCE: dict[str, str] = {
    "hackernews": "the most noteworthy stories with a one-line take",
    "github": "trending repos: what it does and why it stands out",
    "newsapi": "top headlines with context",
    "reddit": "the most noteworthy r/programming discussions with a one-line take",
    "devto": "community articles: topic and why it's worth reading",
    "lobsters": "the most noteworthy stories with a one-line take",
    "arxiv": "papers: research area and key contribution, in plain language",
}


def _highlight_sections() -> str:
    return "\n\n".join(
        f"### {source_label(name)}\n- Bullet points for {hint}"
        for name, hint in SOURCE_GUIDANCE.items()
    )


def _source_sentence() -> str:
    labels = [source_label(name) for name in SOURCE_GUIDANCE]
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


SYSTEM_PROMPT = f"""You are a tech news editor. Given a curated list of articles from \
{_source_sentence()}, generate a concise Markdown digest.

Use the date and source list provided in the user message to fill the title and Sources line.

Output format:
# Tech Digest — <date>
**Sources:** <comma-separated sources>

## Overview
One short paragraph summarizing the main themes across all sources.

## Highlights

{_highlight_sections()}

## Trends
One short paragraph on emerging patterns or recurring topics across sources.

Rules:
- Be concise and factual — no filler phrases
- Use only the articles provided — do not invent URLs, names, or stories
- Keep the total digest under 500 words
- Omit a section entirely if no articles were provided for that source
"""


def build_user_message(articles_markdown: str, today: str, sources: list[str]) -> str:
    """Wrap the formatted articles with the real date and active source list."""
    return (
        f"Date: {today}\n"
        f"Sources: {', '.join(sources)}\n\n"
        f"Generate a digest from the articles below:\n\n{articles_markdown}"
    )
