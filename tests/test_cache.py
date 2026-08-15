from datetime import datetime, timezone

from news_agent.cache import load_cached_digest, save_digest_to_cache
from news_agent.schemas.models import DigestOutput


def _digest(narrative: str = "# Digest") -> DigestOutput:
    return DigestOutput(
        narrative=narrative,
        sources_used=["hackernews"],
        total_articles=1,
        generated_at=datetime.now(timezone.utc),
    )


def test_save_then_load_roundtrips(tmp_path):
    digest = _digest()
    save_digest_to_cache(tmp_path, ["hackernews"], digest)

    loaded = load_cached_digest(tmp_path, ["hackernews"], ttl_seconds=3600)

    assert loaded is not None
    assert loaded.narrative == digest.narrative
    assert loaded.total_articles == digest.total_articles


def test_load_returns_none_when_no_cache_file(tmp_path):
    assert load_cached_digest(tmp_path, ["hackernews"], ttl_seconds=3600) is None


def test_load_returns_none_when_expired(tmp_path):
    save_digest_to_cache(tmp_path, ["hackernews"], _digest())

    assert load_cached_digest(tmp_path, ["hackernews"], ttl_seconds=-1) is None


def test_load_returns_none_for_different_source_set(tmp_path):
    save_digest_to_cache(tmp_path, ["hackernews"], _digest())

    assert load_cached_digest(tmp_path, ["hackernews", "github"], ttl_seconds=3600) is None


def test_load_ignores_corrupt_cache_file(tmp_path):
    save_digest_to_cache(tmp_path, ["hackernews"], _digest())
    cache_dir = tmp_path / ".cache"
    corrupt_file = next(cache_dir.glob("*.json"))
    corrupt_file.write_text("not valid json")

    assert load_cached_digest(tmp_path, ["hackernews"], ttl_seconds=3600) is None


def test_cache_key_is_order_independent(tmp_path):
    """The same source set in a different order must hit the same cache entry."""
    save_digest_to_cache(tmp_path, ["hackernews", "github"], _digest())

    assert load_cached_digest(tmp_path, ["github", "hackernews"], ttl_seconds=3600) is not None


def test_save_digest_leaves_no_temp_file_behind(tmp_path):
    """The write is staged through a sibling temp file and renamed atomically."""
    from news_agent.cache import save_digest_to_cache

    save_digest_to_cache(tmp_path, ["hackernews"], _digest())

    assert list(tmp_path.glob("**/*.tmp")) == []
    assert len(list(tmp_path.glob("**/*.json"))) == 1
