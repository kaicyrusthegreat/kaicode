"""Ollama provider for local model inference."""

from __future__ import annotations

import json
from typing import AsyncIterator, Any

import httpx

from kaicode.providers.base import BaseProvider, Message, StreamChunk, ProviderError


class OllamaProvider(BaseProvider):
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, config) -> None:
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL

    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system: str = "",
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        for m in messages:
            msgs.append({"role": m.role, "content": m.content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise ProviderError(f"Ollama error {response.status_code}: {body.decode()}")
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = data.get("message", {})
                        content = msg.get("content", "")
                        done = data.get("done", False)

                        tool_call = None
                        if msg.get("tool_calls"):
                            raw_tc = msg["tool_calls"][0]
                            fn = raw_tc.get("function", {})
                            tool_call = {
                                "id": f"call_{hash(fn.get('name',''))}",
                                "name": fn.get("name", ""),
                                "input": fn.get("arguments", {}),
                            }

                        usage = None
                        if done and "eval_count" in data:
                            usage = {
                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                "completion_tokens": data.get("eval_count", 0),
                            }

                        yield StreamChunk(
                            content=content,
                            done=done,
                            tool_call=tool_call,
                            usage=usage,
                        )
                        if done:
                            break
            except httpx.ConnectError:
                raise ProviderError(
                    f"Cannot connect to Ollama at {self.base_url}. "
                    "Is Ollama running? Start with: ollama serve"
                )

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
                return []
            except httpx.ConnectError:
                return []

    async def check_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
            except httpx.ConnectError:
                return False
