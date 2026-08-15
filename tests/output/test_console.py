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


def _digest_with_agents(*statuses: tuple[str, bool]) -> DigestOutput:
    from news_agent.schemas.models import AgentStatus

    digest = _digest()
    digest.agents = [
        AgentStatus(name=name, ok=ok, article_count=1 if ok else 0) for name, ok in statuses
    ]
    return digest


def test_render_digest_names_unavailable_sources():
    """A thin digest should say which source was down, not just look empty."""
    out = _render(_digest_with_agents(("hackernews", True), ("arxiv", False)))
    assert "Sources unavailable" in out
    assert "arxiv" in out


def test_render_digest_omits_the_notice_when_every_source_worked():
    out = _render(_digest_with_agents(("hackernews", True), ("github", True)))
    assert "Sources unavailable" not in out


def test_render_digest_shows_when_it_was_generated():
    """With --cache a reused digest is otherwise indistinguishable from a fresh one."""
    from datetime import UTC

    digest = _digest()
    digest.generated_at = datetime(2026, 8, 14, 4, 0, tzinfo=UTC)

    assert "2026-08-14 04:00 UTC" in _render(digest)
