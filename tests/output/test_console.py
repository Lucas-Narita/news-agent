from datetime import datetime
from io import StringIO

from rich.console import Console

from news_agent.schemas.models import DigestOutput


def _digest(
    narrative: str = "# Tech Digest\n\nHello world.",
    sources: tuple[str, ...] = ("hackernews",),
    total: int = 3,
) -> DigestOutput:
    return DigestOutput(
        narrative=narrative,
        sources_used=list(sources),
        total_articles=total,
        generated_at=datetime.now(),
    )


def _render(digest: DigestOutput) -> str:
    from news_agent.output.console import render_digest

    buf = StringIO()
    console = Console(file=buf, width=80)
    render_digest(digest, console=console)
    return buf.getvalue()


def test_render_digest_outputs_narrative():
    out = _render(_digest())
    assert "Hello world" in out


def test_render_digest_shows_article_count_and_sources():
    out = _render(_digest(total=5, sources=("hackernews", "github")))
    assert "5 articles" in out
    assert "hackernews" in out
    assert "github" in out


def test_render_digest_no_sources_still_prints_narrative():
    out = _render(_digest(narrative="No articles available.", sources=(), total=0))
    assert "No articles available" in out
