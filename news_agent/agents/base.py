from abc import ABC, abstractmethod

from news_agent.schemas.models import AgentResult


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AgentResult:
        """Fetch and normalize data. Never raises exceptions."""
        ...
