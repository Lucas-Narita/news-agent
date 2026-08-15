"""The prompt is generated, so these guard the invariants that generation must hold."""

from news_agent.agents.registry import SOURCE_NAMES
from news_agent.llm.prompts import SOURCE_GUIDANCE, SYSTEM_PROMPT, build_user_message


def test_every_registered_source_has_prompt_guidance():
    """A new agent without a section would silently never appear in the digest."""
    assert list(SOURCE_GUIDANCE) == SOURCE_NAMES


def test_system_prompt_has_one_section_per_source():
    assert SYSTEM_PROMPT.count("### ") == len(SOURCE_GUIDANCE)


def test_system_prompt_uses_real_source_names():
    assert "### Hacker News" in SYSTEM_PROMPT
    assert "### arXiv" in SYSTEM_PROMPT
    assert "Hackernews" not in SYSTEM_PROMPT


def test_system_prompt_keeps_the_output_contract():
    assert "# Tech Digest — <date>" in SYSTEM_PROMPT
    assert "## Overview" in SYSTEM_PROMPT
    assert "## Trends" in SYSTEM_PROMPT
    assert "under 500 words" in SYSTEM_PROMPT


def test_build_user_message_carries_date_and_sources():
    message = build_user_message("## Hacker News\n- **X** — https://x.dev", "2026-08-14", ["hackernews"])
    assert "Date: 2026-08-14" in message
    assert "Sources: hackernews" in message
    assert "https://x.dev" in message
