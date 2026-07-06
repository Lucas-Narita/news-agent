import httpx
import respx

ARXIV_URL = "http://export.arxiv.org/api/query"


def _entry_id(i: int) -> str:
    return f"http://arxiv.org/abs/2401.{10000 + i}v1"


def _entry_xml(i: int) -> str:
    return f"""  <entry>
    <id>{_entry_id(i)}</id>
    <published>2026-01-15T18:00:00Z</published>
    <title>
   Paper Title {i}
    </title>
    <summary>
   Abstract summary {i}.
    </summary>
  </entry>
"""


def _entry_missing_title(i: int) -> str:
    return f"""  <entry>
    <id>{_entry_id(i)}</id>
    <published>2026-01-15T18:00:00Z</published>
    <summary>Abstract summary {i}.</summary>
  </entry>
"""


def _entry_missing_id(i: int) -> str:
    return f"""  <entry>
    <published>2026-01-15T18:00:00Z</published>
    <title>Paper Title {i}</title>
    <summary>Abstract summary {i}.</summary>
  </entry>
"""


def _feed(entries_xml: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title type="text">ArXiv Query: search_query=cat:cs.AI</title>
  <id>http://arxiv.org/api/query</id>
{entries_xml}</feed>
"""


def _arxiv_response(n: int = 10) -> httpx.Response:
    entries = "".join(_entry_xml(i) for i in range(n))
    return httpx.Response(200, text=_feed(entries))


async def test_arxiv_happy_path():
    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=_arxiv_response())

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is None
    assert result.source == "arxiv"
    assert len(result.articles) == 10
    assert result.articles[0].source == "arxiv"
    assert result.articles[0].title == "Paper Title 0"
    assert result.articles[0].url == _entry_id(0)
    assert result.articles[0].summary == "Abstract summary 0."
    assert result.articles[0].score is None
    assert result.articles[0].published_at is not None


async def test_arxiv_collapses_multiline_title_and_summary_whitespace():
    """arXiv titles/abstracts wrap across lines with embedded newlines and extra spaces."""
    entry = """  <entry>
    <id>http://arxiv.org/abs/2401.99999v1</id>
    <published>2026-01-15T18:00:00Z</published>
    <title>
   Reasoning About Code
  with Large Language Models
    </title>
    <summary>
   This paper studies how LLMs
   reason about source code   structure.
    </summary>
  </entry>
"""
    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=httpx.Response(200, text=_feed(entry)))

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1
    assert result.articles[0].title == "Reasoning About Code with Large Language Models"
    assert (
        result.articles[0].summary
        == "This paper studies how LLMs reason about source code structure."
    )


async def test_arxiv_skips_entry_missing_title():
    good = _entry_xml(0)
    bad = _entry_missing_title(1)  # one malformed entry must not sink the whole source

    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=httpx.Response(200, text=_feed(good + bad)))

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1


async def test_arxiv_skips_entry_missing_id():
    good = _entry_xml(0)
    bad = _entry_missing_id(1)  # no <id> means no url — must be skipped

    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=httpx.Response(200, text=_feed(good + bad)))

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1


async def test_arxiv_skips_entry_with_malformed_published_date():
    """A malformed <published> value must be skipped, not raise and sink the source."""
    good = _entry_xml(0)
    bad = f"""  <entry>
    <id>{_entry_id(1)}</id>
    <published>not-a-valid-date</published>
    <title>Paper Title 1</title>
    <summary>Abstract summary 1.</summary>
  </entry>
"""

    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=httpx.Response(200, text=_feed(good + bad)))

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 1


async def test_arxiv_api_error():
    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=httpx.Response(503))

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is not None
    assert result.articles == []


async def test_arxiv_retries_on_transient_error():
    with respx.mock:
        respx.get(ARXIV_URL).mock(side_effect=[httpx.Response(503), _arxiv_response(3)])

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.error is None
    assert len(result.articles) == 3


async def test_arxiv_published_at_is_timezone_aware():
    with respx.mock:
        respx.get(ARXIV_URL).mock(return_value=_arxiv_response(1))

        from news_agent.agents.arxiv import ArxivAgent

        agent = ArxivAgent()
        result = await agent.fetch()

    assert result.articles[0].published_at.tzinfo is not None
