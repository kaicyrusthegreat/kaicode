"""Ollama provider for local model inference."""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator, Any

import httpx

from kaicode.providers.base import BaseProvider, Message, StreamChunk, ProviderError


class OllamaProvider(BaseProvider):
    DEFAULT_BASE_URL = "http://localhost:11434"

    # Generation knobs honored from per-provider config (`extra`). All optional —
    # unset means "use Ollama's own default". These let the user trade quality
    # for speed/cost: cap output length, shrink the context window, lower
    # temperature, or keep the model resident longer.
    _OPTION_KEYS = (
        "num_predict",  # max tokens to GENERATE (output cap)
        "num_ctx",  # context window size (smaller = faster prompt eval)
        "temperature",
        "top_p",
        "top_k",
        "repeat_penalty",
        "seed",
        "stop",
    )

    # Models whose reasoning ("thinking") phase can be turned off via the
    # Ollama `think` parameter. Coder variants (qwen3-coder) don't think.
    def _is_thinking_model(self, model: str) -> bool:
        m = model.lower()
        if "coder" in m:
            return False
        return "qwen3" in m or "deepseek-r1" in m

    def __init__(self, config) -> None:
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.extra = getattr(config, "extra", None) or {}

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
            msg: dict = {"role": m.role, "content": m.content}
            if m.tool_calls:
                # Ollama wants arguments as an OBJECT, not a JSON string
                ollama_tcs = []
                for tc in m.tool_calls:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    ollama_tcs.append({"function": {"name": fn.get("name", ""), "arguments": args}})
                msg["tool_calls"] = ollama_tcs
            msgs.append(msg)

        payload: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "stream": True,
            # keep model loaded (default 5m); overridable via config keep_alive
            "keep_alive": self.extra.get("keep_alive", "30m"),
        }
        if tools:
            payload["tools"] = tools

        # Generation options from config (num_predict / num_ctx / temperature …).
        options = {k: self.extra[k] for k in self._OPTION_KEYS if k in self.extra}
        if options:
            payload["options"] = options

        # Reasoning control: for thinking-capable models, skip the reasoning
        # phase by default (much faster, fewer tokens). Re-enable with think:true
        # in config when you want the model to reason. Never sent to non-thinking
        # models, which would reject the parameter.
        if self._is_thinking_model(model) and not kwargs.get("_drop_think"):
            payload["think"] = bool(self.extra.get("think", False))

        try:
            async with self.http.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode()
                    # Older Ollama builds don't know the `think` param — drop it
                    # and retry once so reasoning models still work.
                    if "think" in payload and "think" in body.lower():
                        async for chunk in self.stream_chat(
                            messages, model, system, tools, **{**kwargs, "_drop_think": True}
                        ):
                            yield chunk
                        return
                    raise ProviderError(f"Ollama error {response.status_code}: {body}")
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # Ollama sends errors as {"error": "..."} — catch them
                    if "error" in data:
                        raise ProviderError(f"Ollama: {data['error']}")
                    msg = data.get("message", {})
                    content = msg.get("content", "")
                    done = data.get("done", False)

                    usage = None
                    if done and "eval_count" in data:
                        usage = {
                            "prompt_tokens": data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                        }

                    tool_calls = msg.get("tool_calls") or []
                    if tool_calls:
                        # A single message can carry SEVERAL tool calls (e.g.
                        # creating multiple files at once). Emit one chunk each so
                        # none are silently dropped. Only the last chunk carries
                        # `done`/usage; content rides on the first.
                        for idx, raw_tc in enumerate(tool_calls):
                            fn = raw_tc.get("function", {})
                            last = done and idx == len(tool_calls) - 1
                            yield StreamChunk(
                                content=content if idx == 0 else "",
                                done=last,
                                tool_call={
                                    "id": f"call_{uuid.uuid4().hex[:8]}",
                                    "name": fn.get("name", ""),
                                    "input": fn.get("arguments", {}),
                                },
                                usage=usage if last else None,
                            )
                    else:
                        yield StreamChunk(content=content, done=done, usage=usage)
                    if done:
                        break
        except httpx.ConnectError:
            raise ProviderError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start with: ollama serve"
            )
        except httpx.TimeoutException:
            raise ProviderError(
                f"'{model}' timed out. Large models can be slow to load — "
                "try again (it may be faster once cached), or pick a smaller model."
            )

    async def list_models(self) -> list[str]:
        try:
            response = await self.http.get(f"{self.base_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except httpx.ConnectError:
            return []

    async def check_connection(self) -> bool:
        try:
            response = await self.http.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except httpx.ConnectError:
            return False
