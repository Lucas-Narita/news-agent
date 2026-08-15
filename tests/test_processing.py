from news_agent.processing import deduplicate, rank_by_score
from news_agent.schemas.models import Article


def _article(title: str, url: str, score: int | None = None, source: str = "hackernews") -> Article:
    return Article(title=title, url=url, source=source, score=score)


def test_deduplicate_removes_same_url_keeping_highest_score():
    articles = [
        _article("Same story, low score", "https://example.com/a", score=10, source="hackernews"),
        _article("Same story, high score", "https://example.com/a", score=99, source="reddit"),
        _article("Different story", "https://example.com/b", score=5),
    ]

    result = deduplicate(articles)

    assert len(result) == 2
    kept = next(a for a in result if a.url == "https://example.com/a")
    assert kept.score == 99
    assert kept.source == "reddit"


def test_deduplicate_does_not_mutate_input():
    articles = [
        _article("A", "https://example.com/a", score=1),
        _article("A dup", "https://example.com/a", score=2),
    ]

    deduplicate(articles)

    assert len(articles) == 2  # original list untouched


def test_deduplicate_treats_missing_score_as_lowest():
    articles = [
        _article("No score", "https://example.com/a", score=None),
        _article("Has score", "https://example.com/a", score=0),
    ]

    result = deduplicate(articles)

    assert len(result) == 1
    assert result[0].score == 0  # a real score beats None


def test_rank_by_score_orders_descending():
    articles = [
        _article("low", "https://example.com/a", score=5),
        _article("high", "https://example.com/b", score=50),
        _article("mid", "https://example.com/c", score=20),
    ]

    result = rank_by_score(articles)

    assert [a.score for a in result] == [50, 20, 5]


def test_rank_by_score_puts_none_last():
    articles = [
        _article("none", "https://example.com/a", score=None),
        _article("scored", "https://example.com/b", score=1),
    ]

    result = rank_by_score(articles)

    assert result[0].score == 1
    assert result[1].score is None


def test_canonical_url_strips_tracking_and_trailing_slash():
    from news_agent.processing import canonical_url

    assert canonical_url("HTTPS://Example.com/post/?utm_source=hn&id=7") == (
        "https://example.com/post?id=7"
    )


def test_deduplicate_collapses_urls_differing_only_by_tracking():
    """The same story shared with campaign params is still the same story."""
    from news_agent.processing import deduplicate

    plain = Article(title="Story", url="https://example.com/post", source="hackernews", score=10)
    tagged = Article(
        title="Story",
        url="https://example.com/post/?utm_source=reddit",
        source="reddit",
        score=50,
    )

    result = deduplicate([plain, tagged])

    assert len(result) == 1
    assert result[0].score == 50


def test_deduplicate_keeps_genuinely_different_paths():
    from news_agent.processing import deduplicate

    a = Article(title="A", url="https://example.com/a", source="hackernews")
    b = Article(title="B", url="https://example.com/b", source="hackernews")

    assert len(deduplicate([a, b])) == 2
