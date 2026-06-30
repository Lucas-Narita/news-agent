import asyncio
import logging
from datetime import datetime

from news_agent.agents.devto import DevToAgent
from news_agent.agents.github import GitHubAgent
from news_agent.agents.hackernews import HackerNewsAgent
from news_agent.agents.lobsters import LobstersAgent
from news_agent.agents.newsapi import NewsAPIAgent
from news_agent.agents.reddit import RedditAgent
from news_agent.config import Settings
from news_agent.llm.client import generate_narrative
from news_agent.output.markdown import format_articles
from news_agent.processing import deduplicate, rank_by_score
from news_agent.schemas.models import Article, DigestOutput

logger = logging.getLogger(__name__)

_REGISTRY = {
    "hackernews": HackerNewsAgent,
    "github": GitHubAgent,
    "newsapi": NewsAPIAgent,
    "reddit": RedditAgent,
    "devto": DevToAgent,
    "lobsters": LobstersAgent,
}


async def run_digest(
    sources: list[str], settings: Settings, limit: int | None = None
) -> DigestOutput:
    """Fetch every requested source in parallel, then narrate the survivors.

    Agents never raise — failures arrive as AgentResult.error and are simply skipped,
    so a single dead API degrades the digest instead of breaking the run.
    """
    agents = [_REGISTRY[s]() for s in sources if s in _REGISTRY]
    results = await asyncio.gather(*[agent.fetch() for agent in agents])

    articles: list[Article] = []
    sources_used: list[str] = []
    for result in results:
        if result.error is None:
            articles.extend(result.articles)
            sources_used.append(result.source)
        else:
            logger.warning("source %s failed: %s", result.source, result.error)

    articles = rank_by_score(deduplicate(articles))
    if limit is not None:
        articles = articles[:limit]

    if not articles:
        return DigestOutput(
            narrative="No articles available. All sources failed or returned no results.",
            sources_used=[],
            total_articles=0,
            generated_at=datetime.now(),
        )

    try:
        narrative = await generate_narrative(articles, settings)
    except Exception:
        narrative = (
            "# Tech Digest\n\n"
            "_Narrative generation failed — showing the raw curated list below._\n\n"
            + format_articles(articles)
        )

    return DigestOutput(
        narrative=narrative,
        sources_used=sources_used,
        total_articles=len(articles),
        generated_at=datetime.now(),
    )
