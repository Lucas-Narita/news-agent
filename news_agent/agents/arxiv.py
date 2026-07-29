import xml.etree.ElementTree as ET  # Element type hint only; parsing goes through defusedxml
from datetime import datetime

import defusedxml.ElementTree as safe_ET
import httpx

from news_agent.agents.base import BaseAgent
from news_agent.retry import with_retry
from news_agent.schemas.models import Article

ARXIV_URL = "https://export.arxiv.org/api/query"
SEARCH_QUERY = "cat:cs.AI"
MAX_RESULTS = 10

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _clean_text(raw: str) -> str:
    """Collapse arXiv's wrapped whitespace (embedded newlines, indentation) to one line."""
    return " ".join(raw.split())


def _parse_entry(entry: ET.Element, source: str) -> Article | None:
    """Build an Article from one Atom <entry>, or None if the item is malformed.

    Parsing per-item keeps a single bad entry from sinking the whole source.
    arXiv has no upvote/score concept, so Article.score is always left as None.
    """
    try:
        title_el = entry.find("atom:title", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)
        if title_el is None or not title_el.text:
            return None
        if id_el is None or not id_el.text:
            return None

        summary_el = entry.find("atom:summary", ATOM_NS)
        summary = (
            _clean_text(summary_el.text) if summary_el is not None and summary_el.text else None
        )

        published_el = entry.find("atom:published", ATOM_NS)
        published_at = None
        if published_el is not None and published_el.text:
            published_at = datetime.fromisoformat(published_el.text.strip().replace("Z", "+00:00"))

        return Article(
            title=_clean_text(title_el.text),
            url=id_el.text.strip(),
            source=source,
            summary=summary,
            published_at=published_at,
        )
    except (ValueError, TypeError):
        return None


class ArxivAgent(BaseAgent):
    name = "arxiv"

    async def _fetch_articles(self, client: httpx.AsyncClient) -> list[Article]:
        async def _get():
            resp = await client.get(
                ARXIV_URL,
                params={
                    "search_query": SEARCH_QUERY,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": MAX_RESULTS,
                },
            )
            resp.raise_for_status()
            return resp

        resp = await with_retry(_get)
        root = safe_ET.fromstring(resp.text)
        entries = root.findall("atom:entry", ATOM_NS)

        return [
            article for entry in entries if (article := _parse_entry(entry, self.name)) is not None
        ]
