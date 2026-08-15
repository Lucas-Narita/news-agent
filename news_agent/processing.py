"""Pure, in-memory post-processing for the curated article stream.

These helpers run AFTER agents return and BEFORE the LLM narrates. Keeping them
pure (no I/O, no mutation) means the orchestrator's data-quality rules are unit
testable without touching the network.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from news_agent.schemas.models import Article

# Campaign parameters are appended by whoever shared the link, so the same
# story arrives from Reddit and Dev.to under URLs that differ only in noise.
TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAMS = frozenset({"ref", "ref_src", "fbclid", "gclid"})


def _is_tracking_param(name: str) -> bool:
    return name.startswith(TRACKING_PARAM_PREFIXES) or name in TRACKING_PARAMS


def canonical_url(url: str) -> str:
    """Reduce a URL to the form used for equality, without altering the Article.

    Lowercases scheme and host, drops tracking parameters and a trailing slash.
    Only used as a dedup key — the original URL is what gets rendered, so a
    surprising normalization can never corrupt the output link.
    """
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _is_tracking_param(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _score_key(article: Article) -> tuple[bool, int]:
    """Rank key: a real score always outranks a missing one; ties break by value."""
    return (article.score is not None, article.score or 0)


def deduplicate(articles: list[Article]) -> list[Article]:
    """Collapse articles sharing a URL, keeping the highest-scored copy.

    The same story routinely surfaces on several sources (a Hacker News post and
    its Reddit cross-post point at the same link). We keep whichever copy carries
    the strongest signal and drop the rest. Matching is done on
    ``canonical_url``, so links differing only by tracking parameters or a
    trailing slash still collapse. The input list is never mutated.
    """
    best_by_url: dict[str, Article] = {}
    for article in articles:
        key = canonical_url(article.url)
        current = best_by_url.get(key)
        if current is None or _score_key(article) > _score_key(current):
            best_by_url[key] = article
    return list(best_by_url.values())


def rank_by_score(articles: list[Article]) -> list[Article]:
    """Return a new list ordered by score, highest first, unscored items last."""
    return sorted(articles, key=_score_key, reverse=True)
