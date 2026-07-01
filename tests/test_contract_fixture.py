import json
from datetime import datetime, timezone
from pathlib import Path

from news_agent.schemas.models import AgentStatus, Article, DigestOutput

FIXTURE = Path(__file__).resolve().parents[1] / "web" / "__fixtures__" / "digest.sample.json"


def _canonical_digest() -> DigestOutput:
    return DigestOutput(
        narrative="# Tech Digest\n\nA sample narrative with **markdown**.",
        sources_used=["hackernews", "devto"],
        total_articles=2,
        generated_at=datetime(2026, 7, 1, 4, 0, tzinfo=timezone.utc),
        articles=[
            Article(
                title="A local-first model",
                url="https://example.com/a",
                source="hackernews",
                score=412,
                published_at=datetime(2026, 6, 30, 13, 0, tzinfo=timezone.utc),
                summary=None,
            ),
            Article(
                title="Rust in the kernel",
                url="https://example.com/b",
                source="devto",
                score=210,
                published_at=datetime(2026, 6, 29, 9, 30, tzinfo=timezone.utc),
                summary="A short description.",
            ),
        ],
        agents=[
            AgentStatus(name="hackernews", ok=True, article_count=1),
            AgentStatus(name="devto", ok=True, article_count=1),
            AgentStatus(name="github", ok=False, article_count=0),
        ],
    )


def test_contract_fixture_is_current():
    """Regenerate the fixture and fail if it drifts from what's committed.

    Run `pytest -k contract_fixture` after any schema change, then commit the
    updated file. The frontend (Plan B) parses THIS exact file with Zod.
    """
    expected = _canonical_digest().model_dump_json(indent=2)
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    if not FIXTURE.exists() or FIXTURE.read_text() != expected:
        FIXTURE.write_text(expected)
    assert FIXTURE.read_text() == expected
    DigestOutput.model_validate(json.loads(FIXTURE.read_text()))  # round-trips through the schema
