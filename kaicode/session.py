"""Session management for KaiCode."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from kaicode.providers.base import Message
from kaicode.config import GLOBAL_CONFIG_DIR


SESSIONS_DIR = GLOBAL_CONFIG_DIR / "sessions"


@dataclass
class Session:
    name: str
    provider: str
    model: str
    cwd: str
    messages: list[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.metadata.get("total_tokens", 0)

    def add_tokens(self, count: int) -> None:
        self.metadata["total_tokens"] = self.total_tokens + count
        self.updated_at = time.time()

    def save(self, name: str | None = None) -> Path:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        save_name = name or self.name or f"session_{int(self.created_at)}"
        self.name = save_name
        path = SESSIONS_DIR / f"{save_name}.json"
        data = {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "cwd": self.cwd,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    **({"tool_calls":   m.tool_calls}   if m.tool_calls   else {}),
                    **({"tool_results": m.tool_results} if m.tool_results else {}),
                }
                for m in self.messages
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return path

    @classmethod
    def load(cls, name: str) -> "Session":
        path = SESSIONS_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {name}")
        data = json.loads(path.read_text())
        session = cls(
            name=data["name"],
            provider=data["provider"],
            model=data["model"],
            cwd=data["cwd"],
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            metadata=data.get("metadata", {}),
        )
        for m in data.get("messages", []):
            session.messages.append(Message(
                role=m["role"],
                content=m["content"],
                tool_calls=m.get("tool_calls", []),
                tool_results=m.get("tool_results", []),
            ))
        return session

    @classmethod
    def list_sessions(cls) -> list[dict]:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        sessions = []
        for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text())
                sessions.append({
                    "name": data.get("name", path.stem),
                    "provider": data.get("provider", "?"),
                    "model": data.get("model", "?"),
                    "messages": len(data.get("messages", [])),
                    "updated_at": data.get("updated_at", 0),
                })
            except (json.JSONDecodeError, KeyError):
                pass
        return sessions
