"""Session management for KaiCode."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kaicode.providers.base import Message
from kaicode.config import GLOBAL_CONFIG_DIR


SESSIONS_DIR = GLOBAL_CONFIG_DIR / "sessions"
_SESSION_NAME_MAX = 120
_PATH_SEPARATORS_RE = re.compile(r"[\\/]+")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]+")


def _safe_session_name(name: str | None, fallback: str) -> str:
    """Return a filesystem-safe session name that cannot escape SESSIONS_DIR."""
    raw = (name or fallback).strip()
    safe = _CONTROL_CHARS_RE.sub("", raw)
    safe = _PATH_SEPARATORS_RE.sub("_", safe)
    safe = safe.strip()
    if not safe:
        safe = fallback
    return safe[:_SESSION_NAME_MAX]


def _session_path(name: str) -> Path:
    path = (SESSIONS_DIR / f"{name}.json").resolve()
    root = SESSIONS_DIR.resolve()
    if path.parent != root:
        raise ValueError("Invalid session name.")
    return path


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

    @property
    def total_cost(self) -> float:
        return self.metadata.get("total_cost", 0.0)

    def add_cost(self, cost: float) -> None:
        self.metadata["total_cost"] = self.total_cost + cost
        self.updated_at = time.time()

    def save(self, name: str | None = None) -> Path:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        fallback = self.name or f"session_{int(self.created_at)}"
        save_name = _safe_session_name(name, fallback)
        self.name = save_name
        path = _session_path(save_name)
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
                    **({"tool_calls": m.tool_calls} if m.tool_calls else {}),
                    **({"tool_results": m.tool_results} if m.tool_results else {}),
                }
                for m in self.messages
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return path

    @classmethod
    def load(cls, name: str) -> "Session":
        safe_name = _safe_session_name(name, "")
        if not safe_name:
            raise FileNotFoundError("Session not found: <empty>")
        path = _session_path(safe_name)
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {name}")
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("Session file is corrupted or unreadable.") from exc
        required = {"name", "provider", "model", "cwd"}
        if not required.issubset(data):
            raise ValueError("Session file is missing required fields.")
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
            session.messages.append(
                Message(
                    role=m["role"],
                    content=m["content"],
                    tool_calls=m.get("tool_calls", []),
                    tool_results=m.get("tool_results", []),
                )
            )
        return session

    @classmethod
    def list_sessions(cls) -> list[dict]:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        sessions = []
        for path in sorted(
            SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                data = json.loads(path.read_text())
                sessions.append(
                    {
                        "name": data.get("name", path.stem),
                        "provider": data.get("provider", "?"),
                        "model": data.get("model", "?"),
                        "messages": len(data.get("messages", [])),
                        "updated_at": data.get("updated_at", 0),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return sessions
