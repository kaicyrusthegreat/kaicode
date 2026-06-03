"""Base provider interface for KaiCode."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Any


class ProviderError(Exception):
    pass


@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


@dataclass
class StreamChunk:
    content: str = ""
    done: bool = False
    tool_call: dict | None = None
    usage: dict | None = None


class BaseProvider(ABC):
    """Abstract base class for all AI providers."""

    def __init__(self, config) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system: str = "",
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models."""
        ...

    @abstractmethod
    async def check_connection(self) -> bool:
        """Check if provider is reachable."""
        ...

    def _messages_to_dicts(self, messages: list[Message]) -> list[dict]:
        result = []
        for m in messages:
            d: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_calls:
                d["tool_calls"] = m.tool_calls
            if m.tool_results:
                d["tool_results"] = m.tool_results
            result.append(d)
        return result
