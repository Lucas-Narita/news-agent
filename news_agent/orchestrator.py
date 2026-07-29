import asyncio
import logging
from datetime import datetime, timezone

from news_agent.agents.registry import AGENT_REGISTRY
from news_agent.config import Settings
from news_agent.llm.client import generate_narrative
from news_agent.output.markdown import format_articles
from news_agent.processing import deduplicate, rank_by_score
from news_agent.schemas.models import AgentStatus, Article, DigestOutput

logger = logging.getLogger(__name__)

_REGISTRY = AGENT_REGISTRY


async def run_digest(
    sources: list[str], settings: Settings, limit: int | None = None
) -> DigestOutput:
    """Fetch every requested source in parallel, then narrate the survivors.

    Agents never raise — failures arrive as AgentResult.error and are simply skipped,
    so a single dead API degrades the digest instead of breaking the run. An
    unexpected exception (should a future agent violate that contract) is
    caught via asyncio.gather(return_exceptions=True) and treated the same way.
    """
    agents = [_REGISTRY[s]() for s in sources if s in _REGISTRY]
    # return_exceptions=True is defense in depth: BaseAgent.fetch() already
    # never raises, but a bug in a future agent must degrade that one source
    # instead of crashing the whole digest.
    raw_results = await asyncio.gather(*[agent.fetch() for agent in agents], return_exceptions=True)

    articles: list[Article] = []
    sources_used: list[str] = []
    roster: list[AgentStatus] = []
    for agent, result in zip(agents, raw_results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("source %s raised unexpectedly: %s", agent.name, result)
            roster.append(AgentStatus(name=agent.name, ok=False, article_count=0))
            continue

        roster.append(
            AgentStatus(
                name=result.source,
                ok=result.error is None,
                article_count=len(result.articles),
            )
        )
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
            generated_at=datetime.now(timezone.utc),
            agents=roster,
        )

    try:
        narrative = await generate_narrative(articles, settings)
    except Exception:
        logger.exception("narrative generation failed; falling back to raw list")
        narrative = (
            "# Tech Digest\n\n"
            "_Narrative generation failed — showing the raw curated list below._\n\n"
            + format_articles(articles)
        )

    return DigestOutput(
        narrative=narrative,
        sources_used=sources_used,
        total_articles=len(articles),
        generated_at=datetime.now(timezone.utc),
        articles=articles,
        agents=roster,
    )
