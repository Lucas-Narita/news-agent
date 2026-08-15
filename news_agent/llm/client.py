import logging
from datetime import date

import anthropic

from news_agent.config import Settings
from news_agent.llm.prompts import SYSTEM_PROMPT, build_user_message
from news_agent.output.markdown import format_articles
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

logger = logging.getLogger(__name__)


async def generate_narrative(articles: list[Article], settings: Settings) -> str:
    """Call Claude to turn the curated articles into a Markdown digest.

    The large, fixed SYSTEM_PROMPT is sent as a cached (ephemeral) block so repeated
    runs only pay for the small, varying user message.
    """
    articles_markdown = format_articles(articles)
    today = date.today().isoformat()
    sources = sorted({a.source for a in articles})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _create():
        return await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": build_user_message(articles_markdown, today, sources),
                }
            ],
        )

    # Every source is already retried; the single LLM call was not, so a
    # transient overload threw away a complete fetch and fell back to the raw
    # list. The cached system prompt makes a retry cheap.
    response = await with_retry(_create)
    if response.stop_reason == "max_tokens":
        logger.warning(
            "narrative generation truncated at max_tokens=%d; digest may be incomplete",
            settings.max_tokens,
        )
    text_blocks = [b for b in response.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        return "Narrative unavailable — the model returned no text content."
    # A response may legitimately arrive as several text blocks; taking only the
    # first silently truncated the digest.
    return "\n".join(block.text for block in text_blocks)
