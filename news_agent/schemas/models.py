from datetime import datetime

from pydantic import BaseModel, Field


class Article(BaseModel):
    title: str
    url: str
    source: str
    # Engagement metric normalized across sources (HN/Lobsters points, Reddit
    # upvotes — which can be negative, Dev.to reactions, GitHub stars). None
    # when the source has no such concept (e.g. arXiv).
    score: int | None = None
    published_at: datetime | None = None
    summary: str | None = None


class AgentResult(BaseModel):
    source: str
    articles: list[Article]
    fetched_at: datetime
    error: str | None = None


class AgentStatus(BaseModel):
    name: str
    ok: bool
    article_count: int


class DigestOutput(BaseModel):
    narrative: str
    sources_used: list[str]
    total_articles: int
    generated_at: datetime
    articles: list[Article] = Field(default_factory=list)
    agents: list[AgentStatus] = Field(default_factory=list)
