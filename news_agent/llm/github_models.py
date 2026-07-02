import logging
from datetime import date

import httpx

from news_agent.config import Settings
from news_agent.llm.prompts import SYSTEM_PROMPT, build_user_message
from news_agent.output.markdown import format_articles
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

logger = logging.getLogger(__name__)

GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
MODEL = "openai/gpt-4o-mini"
# The free tier allows 4k output tokens; 2048 gives the ~500-word digest headroom
# without risking a mid-sentence cut.
MAX_TOKENS = 2048
# LLM generation takes far longer than the feed fetches settings.request_timeout
# was tuned for, so this client gets its own ceiling.
LLM_TIMEOUT_SECONDS = 60.0


async def generate_narrative_github(articles: list[Article], settings: Settings) -> str:
    """Call GitHub Models (free tier) to turn the curated articles into a digest.

    Auth is the plain GitHub token: inside GitHub Actions the built-in
    GITHUB_TOKEN works once the workflow grants `models: read`.
    """
    if not settings.github_token:
        raise RuntimeError("GITHUB_TOKEN is required when LLM_PROVIDER=github")

    articles_markdown = format_articles(articles)
    today = date.today().isoformat()
    sources = sorted({a.source for a in articles})

    async def _call() -> httpx.Response:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                GITHUB_MODELS_URL,
                headers={
                    "Authorization": f"Bearer {settings.github_token}",
                    "Accept": "application/vnd.github+json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": build_user_message(articles_markdown, today, sources),
                        },
                    ],
                },
            )
        # Raise inside the retried operation so 5xx triggers a retry;
        # with_retry re-raises 4xx immediately (auth/rate-limit are permanent).
        response.raise_for_status()
        return response

    response = await with_retry(_call)
    choice = response.json()["choices"][0]
    if choice.get("finish_reason") == "length":
        logger.warning("narrative truncated at %d output tokens (finish_reason=length)", MAX_TOKENS)
    content = choice["message"]["content"]
    if not content:
        return "Narrative unavailable — the model returned no text content."
    return content
