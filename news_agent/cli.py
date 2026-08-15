import asyncio
from enum import Enum
from importlib.metadata import version
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from news_agent.agents.registry import SOURCE_NAMES
from news_agent.cache import load_cached_digest, save_digest_to_cache
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


# Only NewsAPI is hard-gated on a key; GITHUB_TOKEN merely raises the rate
# limit, so github stays "ready" without one.
SOURCE_REQUIREMENTS = {"newsapi": "NEWSAPI_KEY"}
SOURCE_SETTING = {"newsapi": "newsapi_key"}


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
        raise typer.Exit(code=1) from None

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

    # Non-secret settings are shown verbatim: they change behaviour just as
    # much as the keys do, and a surprising OUTPUT_DIR is otherwise invisible.
    table.add_row("OUTPUT_DIR", "[green]OK[/green]", str(settings.output_dir))
    table.add_row("REQUEST_TIMEOUT", "[green]OK[/green]", f"{settings.request_timeout}s")
    table.add_row("CACHE_TTL", "[green]OK[/green]", f"{settings.cache_ttl}s")

    console.print(table)


@app.command("sources")
def list_sources():
    """List every registered source and whether it is usable right now."""
    try:
        settings = get_settings()
    except ValidationError:
        settings = None

    table = Table(title="Available Sources")
    table.add_column("Source", style="cyan")
    table.add_column("Status")
    table.add_column("Requires")

    for name in SOURCE_NAMES:
        requires = SOURCE_REQUIREMENTS.get(name, "")
        setting_name = SOURCE_SETTING.get(name)
        has_key = (
            settings is not None
            and setting_name is not None
            and getattr(settings, setting_name, None) is not None
        )
        status = "[green]ready[/green]" if not requires or has_key else "[yellow]needs key[/yellow]"
        table.add_row(name, status, requires or "nothing")

    console.print(table)


def resolve_sources(sources_flag: str | None, settings: Settings) -> list[str]:
    """Return active sources after applying --sources flag and auto-detect.

    A name that is not registered at all is reported on stderr: silently
    dropping it made a typo such as ``--sources hackernwes`` look like a
    successful run over a source that never ran.
    """
    if sources_flag:
        requested = [s.strip() for s in sources_flag.split(",") if s.strip()]
        unknown = [s for s in requested if s not in SOURCE_NAMES]
        if unknown:
            err_console.print(
                f"[yellow]Unknown source(s) ignored: {', '.join(unknown)}. "
                f"Available: {', '.join(SOURCE_NAMES)}[/yellow]"
            )
    else:
        requested = list(settings.default_sources)

    available = dict.fromkeys(SOURCE_NAMES, True)
    available["newsapi"] = settings.newsapi_key is not None

    return [s for s in requested if available.get(s, False)]


@app.command()
def run(
    sources: str | None = typer.Option(
        None,
        "--sources",
        help=f"Comma-separated: {', '.join(SOURCE_NAMES)}",
    ),
    no_file: bool = typer.Option(False, "--no-file", help="Print to terminal only, skip .md file"),
    limit: int | None = typer.Option(
        None,
        "--limit",
        min=1,
        help="Keep only the top N highest-ranked articles",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory to write the digest into [default: OUTPUT_DIR]",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Show INFO-level logs"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.markdown, "--format", help="Output format: markdown or json"
    ),
    cache: bool = typer.Option(
        False, "--cache", help="Reuse a cached digest for the same sources within --cache-ttl"
    ),
    cache_ttl: int | None = typer.Option(
        None,
        "--cache-ttl",
        min=1,
        help="Cache freshness window in seconds (used with --cache) [default: CACHE_TTL]",
    ),
):
    """Fetch tech news and generate a digest."""
    configure_logging(verbose=verbose)
    try:
        settings = get_settings()
    except ValidationError as e:
        missing = [str(error["loc"][0]) for error in e.errors() if error["loc"]]
        if missing:
            fields = ", ".join(f.upper() for f in missing)
            err_console.print(f"[red]Missing required environment variable(s): {fields}.[/red]")
            err_console.print(
                "[dim]Copy .env.example to .env and fill in the values, "
                "or run 'news-agent config check' for the full status.[/dim]"
            )
        else:
            err_console.print(
                "[red]Configuration error. Run 'news-agent config check' for details.[/red]"
            )
        raise typer.Exit(code=1) from None

    # A one-off run into /tmp should not require exporting OUTPUT_DIR; the flag
    # overrides the setting for this invocation only.
    target_dir = output_dir if output_dir is not None else settings.output_dir

    active_sources = resolve_sources(sources, settings)

    if not active_sources:
        err_console.print("[red]No sources available. Check your API keys.[/red]")
        raise typer.Exit(code=1)

    digest = None
    if cache:
        ttl = cache_ttl if cache_ttl is not None else settings.cache_ttl
        digest = load_cached_digest(target_dir, active_sources, ttl)
        if digest is not None:
            err_console.print("[dim]Using cached digest (--cache-ttl not yet expired)[/dim]")

    if digest is None:
        err_console.print(f"[bold]Fetching from:[/bold] {', '.join(active_sources)}")
        try:
            digest = asyncio.run(run_digest(active_sources, settings, limit=limit))
        except Exception as e:
            err_console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1) from None

        if cache:
            save_digest_to_cache(target_dir, active_sources, digest)

    if output_format is OutputFormat.json:
        # stdout stays pure JSON so the digest can be piped into jq or another tool
        content, extension = format_json(digest), "json"
        typer.echo(content)
    else:
        render_digest(digest, console)
        content, extension = digest.narrative, "md"

    if not no_file:
        target_dir.mkdir(parents=True, exist_ok=True)
        # Derived from the digest itself rather than the wall clock: the body is
        # stamped in UTC, so a local-time filename disagreed with its contents,
        # and a --cache hit would have been filed under the wrong hour.
        timestamp = digest.generated_at.strftime("%Y-%m-%d-%H")
        output_path = target_dir / f"digest-{timestamp}.{extension}"
        output_path.write_text(content)
        err_console.print(f"[dim]Saved to {output_path}[/dim]")
