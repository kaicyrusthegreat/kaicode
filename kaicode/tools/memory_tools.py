"""Persistent project memory tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MEMORY_DIR = Path.home() / ".kaicode" / "memory"


def _memory_path(project_root: str) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    slug = Path(project_root).resolve().name
    return MEMORY_DIR / f"{slug}.md"


def read_memory(project_root: str = ".") -> str:
    path = _memory_path(project_root)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def update_memory(content: str, project_root: str = ".") -> dict[str, Any]:
    """Overwrite the entire project memory with new content."""
    path = _memory_path(project_root)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return {"success": True, "path": str(path), "bytes": len(content)}


def clear_memory(project_root: str = ".") -> dict[str, Any]:
    path = _memory_path(project_root)
    if path.exists():
        path.unlink()
        return {"success": True, "message": "Memory cleared."}
    return {"success": True, "message": "No memory to clear."}
