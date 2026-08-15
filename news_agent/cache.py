"""Simple file-based TTL cache for digest results.

Re-running the CLI within the same window (default: 1 hour) would otherwise
redo every network call and pay for a fresh LLM narrative, burning NewsAPI's
100-req/day budget and Claude tokens for no new information. This cache is
intentionally dumb: one JSON file per distinct, sorted source set, keyed by
its own mtime for the TTL check.
"""

import hashlib
import logging
import os
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
        digest = DigestOutput.model_validate_json(path.read_text())
    except Exception:
        logger.warning("cache file %s is unreadable; ignoring", path)
        return None

    logger.info("cache hit for %s (%.0fs old)", ",".join(sorted(sources)), age_seconds)
    return digest


def save_digest_to_cache(output_dir: Path, sources: list[str], digest: DigestOutput) -> None:
    """Persist a digest so the next run within the TTL window can reuse it."""
    path = _cache_path(output_dir, sources)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write-then-rename: an interrupted run (Ctrl-C, OOM) would otherwise leave
    # a half-written file that every later run has to detect and discard.
    # os.replace is atomic within a filesystem, and the temp file is a sibling
    # so the rename never crosses one.
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(digest.model_dump_json(indent=2))
    os.replace(tmp_path, path)
