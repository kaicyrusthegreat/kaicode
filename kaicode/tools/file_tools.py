"""File system tools for the KaiCode agent."""

from __future__ import annotations

import difflib
import os
import subprocess
from pathlib import Path
from typing import Any


def read_file(path: str, start_line: int = 0, end_line: int = 0) -> dict[str, Any]:
    """Read a file's contents, optionally a line range."""
    try:
        start_line = int(start_line)
        end_line   = int(end_line)
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if not p.is_file():
            return {"error": f"Not a file: {path}"}
        if p.stat().st_size > 1_000_000:
            return {"error": f"File too large (>1MB): {path}"}

        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines(keepends=True)
        total = len(lines)

        if start_line > 0 or end_line > 0:
            s = max(0, start_line - 1)
            e = end_line if end_line > 0 else total
            lines = lines[s:e]
            content = "".join(lines)

        return {
            "content": content,
            "path": str(p),
            "total_lines": total,
            "lines_shown": len(lines),
        }
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": str(e)}


def edit_file(path: str, old_content: str, new_content: str) -> dict[str, Any]:
    """Edit a file by replacing old_content with new_content."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"error": f"File not found: {path}"}

        original = p.read_text(encoding="utf-8", errors="replace")
        if old_content not in original:
            return {
                "error": "old_content not found in file. "
                "Make sure to match the exact content including whitespace."
            }

        updated = original.replace(old_content, new_content, 1)

        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{p.name}",
            tofile=f"b/{p.name}",
            n=3,
        ))

        p.write_text(updated, encoding="utf-8")
        return {
            "success": True,
            "path": str(p),
            "diff": "".join(diff),
        }
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": str(e)}


def create_directory(path: str) -> dict[str, Any]:
    """Create a new directory (and any missing parent directories)."""
    try:
        p = Path(path).expanduser().resolve()
        existed = p.exists()
        p.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "path": str(p),
            "action": "already existed" if existed else "created",
        }
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": str(e)}


def create_file(path: str, content: str) -> dict[str, Any]:
    """Create a new file (or overwrite if it exists)."""
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "path": str(p),
            "action": "overwritten" if existed else "created",
        }
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": str(e)}


def list_files(
    path: str = ".",
    depth: int = 2,
    include_hidden: bool = False,
) -> dict[str, Any]:
    """List files in a directory tree."""
    try:
        depth          = int(depth)
        include_hidden = str(include_hidden).lower() not in ("false", "0", "")
        root = Path(path).expanduser().resolve()
        if not root.exists():
            return {"error": f"Path not found: {path}"}
        if not root.is_dir():
            return {"error": f"Not a directory: {path}"}

        entries = []
        _walk_tree(root, root, depth, 0, entries, include_hidden)
        return {"path": str(root), "entries": entries}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": str(e)}


def _walk_tree(
    root: Path,
    current: Path,
    max_depth: int,
    current_depth: int,
    entries: list,
    include_hidden: bool,
) -> None:
    IGNORE = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".tox", "dist", "build", ".eggs", "*.egg-info",
        ".DS_Store", ".mypy_cache", ".pytest_cache",
    }
    if current_depth > max_depth:
        return

    try:
        items = sorted(current.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return

    for item in items:
        if not include_hidden and item.name.startswith("."):
            continue
        if item.name in IGNORE or any(item.match(p) for p in IGNORE):
            continue

        rel = item.relative_to(root)
        entries.append({
            "path": str(rel),
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
        if item.is_dir() and current_depth < max_depth:
            _walk_tree(root, item, max_depth, current_depth + 1, entries, include_hidden)


def run_command(
    command: str,
    cwd: str = ".",
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute a shell command and return the output."""
    timeout = int(timeout)
    BLOCKED = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
    for blocked in BLOCKED:
        if blocked in command:
            return {"error": f"Blocked dangerous command pattern: {blocked}"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s: {command}"}
    except Exception as e:
        return {"error": str(e)}
