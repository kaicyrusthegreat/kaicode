"""OpenAI provider for KaiCode."""

from __future__ import annotations

import json
from typing import AsyncIterator, Any

import httpx

from kaicode.providers.base import BaseProvider, Message, StreamChunk, ProviderError


OPENAI_API_BASE = "https://api.openai.com/v1"


class OpenAIProvider(BaseProvider):
    DEFAULT_MODEL = "gpt-4o"

    @property
    def api_base(self) -> str:
        return self.config.base_url or OPENAI_API_BASE

    def _build_messages(self, messages: list[Message], system: str = "") -> list[dict]:
        """Convert internal messages to OpenAI wire format with correct tool linkage."""
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                # Tool result — must carry tool_call_id to link back to the call
                tcid = m.tool_results[0]["tool_use_id"] if m.tool_results else ""
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": tcid,
                        "content": m.content,
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                # Assistant turn that issued tool calls — content may be empty
                msgs.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": m.tool_calls,
                    }
                )
            else:
                msgs.append({"role": m.role, "content": m.content})
        return msgs

    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system: str = "",
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        if not self.config.api_key:
            raise ProviderError(
                "OpenAI API key not set. "
                "Set OPENAI_API_KEY env var or add to ~/.kaicode/config.yaml"
            )

        msgs = self._build_messages(messages, system)

        payload: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self.http.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise ProviderError(f"OpenAI error {response.status_code}: {body.decode()}")

                tool_calls_partial: dict[int, dict] = {}
                usage: dict | None = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        yield StreamChunk(done=True, usage=usage)
                        break
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if "usage" in data and data["usage"]:
                        u = data["usage"]
                        usage = {
                            "prompt_tokens": u.get("prompt_tokens", 0),
                            "completion_tokens": u.get("completion_tokens", 0),
                        }

                    choices = data.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    finish = choices[0].get("finish_reason")

                    if delta.get("content"):
                        yield StreamChunk(content=delta["content"])

                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_partial:
                                tool_calls_partial[idx] = {
                                    "id": "",
                                    "name": "",
                                    "input_str": "",
                                }
                            if tc.get("id"):
                                tool_calls_partial[idx]["id"] = tc["id"]
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                tool_calls_partial[idx]["name"] = fn["name"]
                            if fn.get("arguments"):
                                tool_calls_partial[idx]["input_str"] += fn["arguments"]

                    if finish == "tool_calls":
                        for tc in tool_calls_partial.values():
                            try:
                                inp = json.loads(tc["input_str"])
                            except json.JSONDecodeError:
                                inp = {}
                            yield StreamChunk(
                                tool_call={
                                    "id": tc["id"],
                                    "name": tc["name"],
                                    "input": inp,
                                }
                            )

        except httpx.ConnectError:
            raise ProviderError("Cannot connect to OpenAI API.")

    async def list_models(self) -> list[str]:
        if not self.config.api_key:
            return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        try:
            response = await self.http.get(
                f"{self.api_base}/models",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = [
                    m["id"]
                    for m in data.get("data", [])
                    if "gpt" in m["id"] or "o1" in m["id"] or "o3" in m["id"]
                ]
                return sorted(models)
        except httpx.ConnectError:
            pass
        return ["gpt-4o", "gpt-4o-mini"]

    async def check_connection(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            response = await self.http.get(
                f"{self.api_base}/models",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=10.0,
            )
            return response.status_code == 200
        except httpx.ConnectError:
            return False
