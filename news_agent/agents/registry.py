"""Single source of truth for agent source names.

Adding a new agent means registering it here once; orchestrator, CLI and
config all read from this module instead of maintaining their own copies.
"""

from collections.abc import Mapping
from types import MappingProxyType

from news_agent.agents.arxiv import ArxivAgent
from news_agent.agents.base import BaseAgent
from news_agent.agents.devto import DevToAgent
from news_agent.agents.github import GitHubAgent
from news_agent.agents.hackernews import HackerNewsAgent
from news_agent.agents.lobsters import LobstersAgent
from news_agent.agents.newsapi import NewsAPIAgent
from news_agent.agents.reddit import RedditAgent

# Read-only: the registry is process-wide shared state, and Settings and the
# CLI both derive their source list from it. A stray mutation would silently
# change what every later caller sees.
AGENT_REGISTRY: Mapping[str, type[BaseAgent]] = MappingProxyType({
    "hackernews": HackerNewsAgent,
    "github": GitHubAgent,
    "newsapi": NewsAPIAgent,
    "reddit": RedditAgent,
    "devto": DevToAgent,
    "lobsters": LobstersAgent,
    "arxiv": ArxivAgent,
})

SOURCE_NAMES: list[str] = list(AGENT_REGISTRY.keys())
