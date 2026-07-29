"""Simple file-based TTL cache for digest results.

Re-running the CLI within the same window (default: 1 hour) would otherwise
redo every network call and pay for a fresh LLM narrative, burning NewsAPI's
100-req/day budget and Claude tokens for no new information. This cache is
intentionally dumb: one JSON file per distinct, sorted source set, keyed by
its own mtime for the TTL check.
"""

import hashlib
import json
import logging
from pathlib import Path
from time import time

from news_agent.schemas.models import DigestOutput

logger = logging.getLogger(__name__)

CACHE_SUBDIR = ".cache"


def _cache_path(output_dir: Path, sources: list[str]) -> Path:
    key = ",".join(sorted(sources))
    digest_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    return output_dir / CACHE_SUBDIR / f"{digest_hash}.json"


def load_cached_digest(
    output_dir: Path, sources: list[str], ttl_seconds: float
) -> DigestOutput | None:
    """Return a cached DigestOutput if a fresh-enough one exists, else None.

    Any read/parse failure is treated as a cache miss rather than an error —
    a stale or corrupt cache file should never block a normal run.
    """
    path = _cache_path(output_dir, sources)
    if not path.exists():
        return None

    age_seconds = time() - path.stat().st_mtime
    if age_seconds > ttl_seconds:
        return None

    try:
        return DigestOutput.model_validate_json(path.read_text())
    except Exception:
        logger.warning("cache file %s is unreadable; ignoring", path)
        return None


def save_digest_to_cache(output_dir: Path, sources: list[str], digest: DigestOutput) -> None:
    """Persist a digest so the next run within the TTL window can reuse it."""
    path = _cache_path(output_dir, sources)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json.loads(digest.model_dump_json()), indent=2))
