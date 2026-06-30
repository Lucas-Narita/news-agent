import json
from datetime import datetime

from news_agent.output.json_output import format_json
from news_agent.schemas.models import Article, DigestOutput


def _digest() -> DigestOutput:
    return DigestOutput(
        narrative="# Tech Digest",
        sources_used=["hackernews"],
        total_articles=1,
        generated_at=datetime(2026, 5, 1, 12, 0, 0),
        articles=[Article(title="A", url="https://example.com/a", source="hackernews", score=10)],
    )


def test_format_json_produces_valid_json():
    payload = format_json(_digest())
    data = json.loads(payload)

    assert data["narrative"] == "# Tech Digest"
    assert data["total_articles"] == 1
    assert data["sources_used"] == ["hackernews"]


def test_format_json_includes_structured_articles():
    payload = format_json(_digest())
    data = json.loads(payload)

    assert len(data["articles"]) == 1
    assert data["articles"][0]["url"] == "https://example.com/a"
    assert data["articles"][0]["score"] == 10
