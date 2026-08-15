from news_agent.schemas.models import Article


def _article(
    source: str,
    title: str = "Title",
    score: int | None = None,
    summary: str | None = None,
) -> Article:
    return Article(
        title=title, url="https://example.com", source=source, score=score, summary=summary
    )


def test_format_articles_empty_list():
    from news_agent.output.markdown import format_articles

    assert format_articles([]) == ""


def test_format_articles_groups_by_source():
    from news_agent.output.markdown import format_articles

    articles = [
        _article("hackernews", title="HN Story"),
        _article("github", title="owner/repo"),
    ]
    result = format_articles(articles)
    assert "## Hacker News" in result
    assert "## GitHub" in result
    assert "HN Story" in result
    assert "owner/repo" in result


def test_format_articles_uses_real_source_names():
    """Slugs render the way the communities spell themselves, not capitalize()."""
    from news_agent.output.markdown import format_articles

    result = format_articles([_article("devto"), _article("arxiv")])
    assert "## Dev.to" in result
    assert "## arXiv" in result


def test_source_label_falls_back_to_capitalized_slug():
    """An unregistered source still renders readably instead of crashing."""
    from news_agent.output.markdown import source_label

    assert source_label("mastodon") == "Mastodon"


def test_format_articles_github_shows_stars():
    from news_agent.output.markdown import format_articles

    articles = [_article("github", title="owner/repo", score=1200)]
    result = format_articles(articles)
    assert "★1200" in result


def test_format_articles_hackernews_shows_score():
    from news_agent.output.markdown import format_articles

    articles = [_article("hackernews", title="HN Story", score=342)]
    result = format_articles(articles)
    assert "(score: 342)" in result


def test_format_articles_includes_summary():
    from news_agent.output.markdown import format_articles

    articles = [_article("newsapi", title="News Title", summary="A brief description.")]
    result = format_articles(articles)
    assert "A brief description." in result


def test_format_articles_no_score_no_decoration():
    from news_agent.output.markdown import format_articles

    articles = [_article("newsapi", title="News Title")]
    result = format_articles(articles)
    assert "(score:" not in result
    assert "★" not in result
