"""Pure, in-memory post-processing for the curated article stream.

These helpers run AFTER agents return and BEFORE the LLM narrates. Keeping them
pure (no I/O, no mutation) means the orchestrator's data-quality rules are unit
testable without touching the network.
"""

from news_agent.schemas.models import Article


def _score_key(article: Article) -> tuple[bool, int]:
    """Rank key: a real score always outranks a missing one; ties break by value."""
    return (article.score is not None, article.score or 0)


def deduplicate(articles: list[Article]) -> list[Article]:
    """Collapse articles sharing a URL, keeping the highest-scored copy.

    The same story routinely surfaces on several sources (a Hacker News post and
    its Reddit cross-post point at the same link). We keep whichever copy carries
    the strongest signal and drop the rest. The input list is never mutated.
    """
    best_by_url: dict[str, Article] = {}
    for article in articles:
        current = best_by_url.get(article.url)
        if current is None or _score_key(article) > _score_key(current):
            best_by_url[article.url] = article
    return list(best_by_url.values())


def rank_by_score(articles: list[Article]) -> list[Article]:
    """Return a new list ordered by score, highest first, unscored items last."""
    return sorted(articles, key=_score_key, reverse=True)
