from datetime import date

import anthropic

from news_agent.config import Settings
from news_agent.llm.prompts import SYSTEM_PROMPT, build_user_message
from news_agent.output.markdown import format_articles
from news_agent.schemas.models import Article

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024


async def generate_narrative(articles: list[Article], settings: Settings) -> str:
    """Call Claude to turn the curated articles into a Markdown digest.

    The large, fixed SYSTEM_PROMPT is sent as a cached (ephemeral) block so repeated
    runs only pay for the small, varying user message.
    """
    articles_markdown = format_articles(articles)
    today = date.today().isoformat()
    sources = sorted({a.source for a in articles})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
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
    text_blocks = [b for b in response.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        return "Narrative unavailable — the model returned no text content."
    return text_blocks[0].text
