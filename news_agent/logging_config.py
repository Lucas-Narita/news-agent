"""Logging setup for the CLI entry point.

The library code only ever calls ``logging.getLogger(__name__)``; wiring the
handler is the application's job. This keeps the orchestrator and agents free of
any opinion about where logs go.
"""

import logging

from rich.logging import RichHandler


def configure_logging(verbose: bool = False) -> None:
    """Attach a Rich handler to the ``news_agent`` logger.

    INFO and above when ``verbose`` is set, otherwise WARNING and above. Calling
    this more than once is safe — the handler is only attached on the first call.
    """
    level = logging.INFO if verbose else logging.WARNING
    logger = logging.getLogger("news_agent")
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(RichHandler(rich_tracebacks=True, show_path=False))
