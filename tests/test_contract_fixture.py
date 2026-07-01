import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from news_agent.schemas.models import AgentStatus, Article, DigestOutput

FIXTURE = Path(__file__).resolve().parents[1] / "web" / "__fixtures__" / "digest.sample.json"


def _canonical_digest() -> DigestOutput:
    return DigestOutput(
        narrative="# Tech Digest\n\nA sample narrative with **markdown**.",
        sources_used=["hackernews", "devto", "lobsters"],
        total_articles=3,
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
            Article(
                title="Why static site generators still matter",
                url="https://lobste.rs/s/ab12cd/why_static_site_generators_still_matter",
                source="lobsters",
                score=None,
                published_at=datetime(2026, 6, 30, 21, 30, tzinfo=timezone(timedelta(hours=-6))),
                summary="A community discussion on keeping build tooling simple.",
            ),
        ],
        agents=[
            AgentStatus(name="hackernews", ok=True, article_count=1),
            AgentStatus(name="devto", ok=True, article_count=1),
            AgentStatus(name="lobsters", ok=True, article_count=1),
            AgentStatus(name="github", ok=False, article_count=0),
        ],
    )


def _expected_fixture_text() -> str:
    """Canonical JSON the committed fixture must match, trailing newline included."""
    return _canonical_digest().model_dump_json(indent=2) + "\n"


def regenerate_fixture() -> None:
    """Deliberately refresh the committed fixture from the canonical schema.

    This is the ONLY sanctioned way to change the fixture. Run it explicitly
    after an intentional schema change:

        python tests/test_contract_fixture.py

    then review the diff and commit the updated file. It is never invoked by
    the default `pytest` run, so drift can't be laundered into a green test.
    """
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(_expected_fixture_text())
    print(f"Regenerated {FIXTURE}")


def test_contract_fixture_is_current():
    """Fail if the committed fixture drifts from the DigestOutput schema.

    The frontend (Plan B) parses THIS exact file with Zod, so it must never
    silently diverge from the schema. If this test fails, either the schema
    change was intentional (run `python tests/test_contract_fixture.py` to
    regenerate the fixture, review the diff, and commit it) or it was not
    (fix the schema/serialization instead).
    """
    original = FIXTURE.read_text() if FIXTURE.exists() else None
    expected = _expected_fixture_text()

    assert original == expected, (
        "web/__fixtures__/digest.sample.json has drifted from the DigestOutput "
        "schema. Run `python tests/test_contract_fixture.py` to regenerate it, "
        "review the diff, then commit the updated fixture."
    )

    # Round-trip through the schema to guarantee the fixture is still valid input.
    DigestOutput.model_validate(json.loads(original))


if __name__ == "__main__":
    regenerate_fixture()
