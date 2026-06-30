import asyncio
from datetime import datetime
from enum import Enum
from importlib.metadata import version
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from news_agent.config import Settings, get_settings
from news_agent.logging_config import configure_logging
from news_agent.orchestrator import run_digest
from news_agent.output.console import render_digest
from news_agent.output.json_output import format_json

app = typer.Typer(help="news-agent: tech news digest powered by Claude.")
config_app = typer.Typer(help="Configuration commands.")
app.add_typer(config_app, name="config")

console = Console()
err_console = Console(stderr=True)  # diagnostics go to stderr, keeping stdout clean


class OutputFormat(str, Enum):
    markdown = "markdown"
    json = "json"


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"news-agent {version('news-agent')}")
        raise typer.Exit()


@app.callback()
def main(
    version_flag: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """news-agent: tech news digest powered by Claude."""


@config_app.command("check")
def config_check():
    """Validate environment variables and display their status."""
    try:
        settings = get_settings()
    except ValidationError as e:
        console.print("[red]Configuration error:[/red]")
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            console.print(f"  [red]x[/red] {field}: {error['msg']}")
        raise typer.Exit(code=1)

    table = Table(title="Configuration Status")
    table.add_column("Variable", style="cyan")
    table.add_column("Status")
    table.add_column("Value")

    table.add_row(
        "ANTHROPIC_API_KEY",
        "[green]OK[/green]",
        "***" + settings.anthropic_api_key[-4:],
    )

    if settings.newsapi_key:
        table.add_row("NEWSAPI_KEY", "[green]OK[/green]", "***" + settings.newsapi_key[-4:])
    else:
        table.add_row("NEWSAPI_KEY", "[yellow]OPTIONAL[/yellow]", "not set")

    if settings.github_token:
        table.add_row("GITHUB_TOKEN", "[green]OK[/green]", "***" + settings.github_token[-4:])
    else:
        table.add_row("GITHUB_TOKEN", "[yellow]OPTIONAL[/yellow]", "not set")

    console.print(table)


def resolve_sources(sources_flag: Optional[str], settings: Settings) -> list[str]:
    """Return active sources after applying --sources flag and auto-detect."""
    if sources_flag:
        requested = [s.strip() for s in sources_flag.split(",")]
    else:
        requested = list(settings.default_sources)

    available = {
        "hackernews": True,
        "github": True,
        "newsapi": settings.newsapi_key is not None,
        "reddit": True,
        "devto": True,
        "lobsters": True,
    }

    return [s for s in requested if available.get(s, False)]


@app.command()
def run(
    sources: Optional[str] = typer.Option(
        None, "--sources", help="Comma-separated: hackernews, github, newsapi"
    ),
    no_file: bool = typer.Option(False, "--no-file", help="Print to terminal only, skip .md file"),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Keep only the top N highest-ranked articles"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Show INFO-level logs"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.markdown, "--format", help="Output format: markdown or json"
    ),
):
    """Fetch tech news and generate a digest."""
    configure_logging(verbose=verbose)
    try:
        settings = get_settings()
    except ValidationError:
        console.print("[red]Configuration error. Run 'news-agent config check' for details.[/red]")
        raise typer.Exit(code=1)

    active_sources = resolve_sources(sources, settings)

    if not active_sources:
        console.print("[red]No sources available. Check your API keys.[/red]")
        raise typer.Exit(code=1)

    err_console.print(f"[bold]Fetching from:[/bold] {', '.join(active_sources)}")

    try:
        digest = asyncio.run(run_digest(active_sources, settings, limit=limit))
    except Exception as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

    if output_format is OutputFormat.json:
        # stdout stays pure JSON so the digest can be piped into jq or another tool
        content, extension = format_json(digest), "json"
        typer.echo(content)
    else:
        render_digest(digest, console)
        content, extension = digest.narrative, "md"

    if not no_file:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H")
        output_path = settings.output_dir / f"digest-{timestamp}.{extension}"
        output_path.write_text(content)
        err_console.print(f"[dim]Saved to {output_path}[/dim]")
