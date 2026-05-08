from datetime import datetime

import pytest
from pydantic import ValidationError

from news_agent.schemas.models import AgentResult, Article, DigestOutput


def test_article_requires_title_url_source():
    with pytest.raises(ValidationError):
        Article(url="https://example.com", source="hackernews")


def test_article_optional_fields_default_to_none():
    a = Article(title="Test", url="https://example.com", source="hackernews")
    assert a.score is None
    assert a.summary is None
    assert a.published_at is None


def test_agent_result_graceful_error():
    r = AgentResult(
        source="newsapi",
        articles=[],
        fetched_at=datetime.now(),
        error="NEWSAPI_KEY not configured",
    )
    assert r.error == "NEWSAPI_KEY not configured"
    assert r.articles == []


def test_agent_result_no_error_by_default():
    r = AgentResult(source="hackernews", articles=[], fetched_at=datetime.now())
    assert r.error is None


def test_digest_output():
    d = DigestOutput(
        narrative="Top stories this hour.",
        sources_used=["hackernews", "github"],
        total_articles=10,
        generated_at=datetime.now(),
    )
    assert d.total_articles == 10
    assert "hackernews" in d.sources_used
