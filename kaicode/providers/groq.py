"""Groq provider for KaiCode (fast inference)."""

from __future__ import annotations

from typing import AsyncIterator, Any

from kaicode.providers.base import BaseProvider, Message, StreamChunk, ProviderError
from kaicode.providers.openai import OpenAIProvider


GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqProvider(OpenAIProvider):
    DEFAULT_MODEL = "llama-3.1-70b-versatile"

    @property
    def api_base(self) -> str:
        return self.config.base_url or GROQ_API_BASE

    async def list_models(self) -> list[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "gemma-7b-it",
        ]

    async def check_connection(self) -> bool:
        if not self.config.api_key:
            return False
        import httpx

        try:
            response = await self.http.get(
                f"{self.api_base}/models",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=10.0,
            )
            return response.status_code == 200
        except httpx.ConnectError:
            return False
