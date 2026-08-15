from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Article(BaseModel):
    # Articles are built from third-party JSON/XML, where a padded or empty
    # string is a normal accident. Validating at this boundary means a bad item
    # is rejected by the agent that parsed it, not silently rendered as an
    # empty bullet in the digest.
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    source: str = Field(min_length=1)
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
    name: str = Field(min_length=1)
    ok: bool
    # Counts are cardinalities: a negative value is always a bug upstream, and
    # catching it here beats rendering "-3 articles" in the digest footer.
    article_count: int = Field(ge=0)


class DigestOutput(BaseModel):
    narrative: str
    sources_used: list[str]
    total_articles: int = Field(ge=0)
    generated_at: datetime
    articles: list[Article] = Field(default_factory=list)
    agents: list[AgentStatus] = Field(default_factory=list)
