from news_agent.config import Settings
from news_agent.schemas.models import DigestOutput


async def run_digest(sources: list[str], settings: Settings) -> DigestOutput:
    raise NotImplementedError("Implemented in Section 5")
