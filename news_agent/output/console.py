from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from news_agent.schemas.models import DigestOutput


def render_digest(digest: DigestOutput, console: Console | None = None) -> None:
    """Pretty-print a digest to the terminal: Markdown body + a metadata footer.

    The console is injectable so rendering can be captured in tests without a TTY.
    """
    console = console or Console()
    console.print(Markdown(digest.narrative))

    if digest.sources_used:
        meta = f"{digest.total_articles} articles | sources: {', '.join(digest.sources_used)}"
        console.print(Panel(meta, expand=False, border_style="dim"))

    # A source that failed contributed nothing to sources_used, so without this
    # the digest just looks thin — with no hint that arXiv was down.
    failed = [agent.name for agent in digest.agents if not agent.ok]
    if failed:
        console.print(f"[yellow]Sources unavailable:[/yellow] {', '.join(failed)}")
