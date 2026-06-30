"""Machine-readable rendering of the digest.

While markdown.py and console.py target human readers, this renders the digest
as JSON so the agent can be composed into a pipeline (e.g. piped into ``jq`` or
consumed by another service).
"""

from news_agent.schemas.models import DigestOutput


def format_json(digest: DigestOutput) -> str:
    """Serialize the digest as indented JSON, including the structured articles."""
    return digest.model_dump_json(indent=2)
