"""Base provider interface for KaiCode."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Any

import httpx


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
        self._http: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def http(self) -> httpx.AsyncClient:
        """Long-lived pooled HTTP client — reuses TCP/TLS connections across turns."""
        if self._http is None or self._http.is_closed:
            # Generous read timeout: large local models (14-20GB) can take
            # well over a minute just to load into memory before the first
            # token. connect stays short; read/pool are long.
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(600.0, connect=10.0),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=90.0,
                ),
            )
        return self._http

    async def aclose(self) -> None:
        """Close the pooled client (called when switching providers / on exit)."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None

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
