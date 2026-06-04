"""CyrusAI provider — kaicode's window into the self-improving brain.

Selecting the `cyrusai` model turns every turn into a learning experience:

    RECALL  relevant past lessons  -> inject them into the system prompt
    STREAM  the answer from the student model (via Ollama)
    LEARN   (in the background) teacher judges the answer -> reflect -> credit

The student model and memory live in the separate `cyrusai` package; this
provider just wires kaicode's chat loop into it. Streaming itself is delegated
to the existing OllamaProvider so we don't duplicate transport code.
"""

from __future__ import annotations

import asyncio
import threading
from typing import AsyncIterator, Any

from kaicode.providers.base import BaseProvider, Message, StreamChunk
from kaicode.providers.ollama import OllamaProvider

from cyrusai import CyrusAI
from cyrusai import config as cyrus_config


class CyrusAIProvider(BaseProvider):
    """Exposes CyrusAI as a single selectable model named ``cyrusai``."""

    MODEL_NAME = "cyrusai"

    def __init__(self, config) -> None:
        super().__init__(config)
        # The student model actually generates tokens; defaults to CyrusAI's own.
        self.student_model = config.extra.get("student_model") or cyrus_config.STUDENT_MODEL
        # Reuse the Ollama transport for streaming (shares pooled HTTP, base_url).
        self._ollama = OllamaProvider(config)
        # One shared brain, guarded by a lock (background learning runs in a thread).
        self._brain = CyrusAI()
        self._lock = threading.Lock()

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _latest_user_text(messages: list[Message]) -> str:
        for m in reversed(messages):
            if m.role == "user" and m.content.strip():
                return m.content.strip()
        return ""

    def _recall(self, task: str) -> tuple[list[str], str]:
        with self._lock:
            lessons, ctx = self._brain.recall_context(task)
            return [l.id for l in lessons], ctx

    def _learn(self, task: str, answer: str, lesson_ids: list[str]) -> None:
        # Runs in a background thread; learning must never crash a chat turn.
        try:
            with self._lock:
                self._brain.learn_from_turn(task, answer, lesson_ids)
        except Exception:
            pass

    # --- BaseProvider API --------------------------------------------------
    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        system: str = "",
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        task = self._latest_user_text(messages)

        # 1. RECALL — pull relevant lessons and fold them into the system prompt.
        lesson_ids: list[str] = []
        aug_system = system
        if task:
            try:
                lesson_ids, ctx = await asyncio.to_thread(self._recall, task)
                if ctx:
                    aug_system = (system + "\n\n" + ctx).strip() if system else ctx
            except Exception:
                pass  # never let memory issues block answering

        # 2. STREAM — the student model answers (with the recalled context).
        # 3. LEARN — scheduled the moment the final chunk arrives, BEFORE we yield
        #    it. Consumers (kaicode included) break on `done`, which would freeze
        #    this generator at the yield and skip any trailing code — so the
        #    background learning must be launched here, not after the loop.
        parts: list[str] = []
        learning_started = False
        async for chunk in self._ollama.stream_chat(
            messages, model=self.student_model, system=aug_system, tools=tools, **kwargs
        ):
            if chunk.content:
                parts.append(chunk.content)
            if chunk.done and not learning_started:
                learning_started = True
                answer = "".join(parts).strip()
                if task and answer:
                    asyncio.create_task(
                        asyncio.to_thread(self._learn, task, answer, lesson_ids)
                    )
            yield chunk

    async def list_models(self) -> list[str]:
        return [self.MODEL_NAME]

    async def check_connection(self) -> bool:
        # CyrusAI is reachable iff its underlying Ollama runtime is up.
        return await self._ollama.check_connection()

    async def aclose(self) -> None:
        await self._ollama.aclose()
        await super().aclose()
