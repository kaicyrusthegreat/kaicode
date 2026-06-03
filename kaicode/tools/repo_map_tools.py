"""Repo map — a compact index of the codebase's files and top-level symbols."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".tox",
    "dist", "build", ".eggs", ".mypy_cache", ".pytest_cache", ".next",
}
_SOURCE_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".dart", ".go", ".rs",
    ".rb", ".java", ".kt", ".swift", ".vue",
}

# Regex symbol extractors for non-Python languages
_DEF_PATTERNS = {
    ".js":   r'^\s*(?:export\s+)?(?:async\s+)?(?:function|class)\s+(\w+)',
    ".ts":   r'^\s*(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|enum)\s+(\w+)',
    ".tsx":  r'^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const)\s+(\w+)',
    ".jsx":  r'^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const)\s+(\w+)',
    ".dart": r'^\s*(?:class|mixin|enum)\s+(\w+)',
    ".go":   r'^\s*func\s+(?:\([^)]*\)\s*)?(\w+)|^\s*type\s+(\w+)',
    ".rs":   r'^\s*(?:pub\s+)?(?:fn|struct|enum|trait)\s+(\w+)',
    ".rb":   r'^\s*(?:def|class|module)\s+(\w+)',
    ".java": r'^\s*(?:public|private|protected)?\s*(?:class|interface|enum)\s+(\w+)',
    ".kt":   r'^\s*(?:fun|class|object|interface)\s+(\w+)',
    ".swift":r'^\s*(?:func|class|struct|enum|protocol)\s+(\w+)',
}


def _python_symbols(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    syms = []
    for node in tree.body:   # top-level only — keeps it compact
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            syms.append(f"{node.name}()")
        elif isinstance(node, ast.ClassDef):
            syms.append(node.name)
    return syms


def _regex_symbols(text: str, ext: str) -> list[str]:
    pat = _DEF_PATTERNS.get(ext)
    if not pat:
        return []
    syms = []
    for m in re.finditer(pat, text, re.M):
        name = next((g for g in m.groups() if g), None)
        if name and name not in syms:
            syms.append(name)
    return syms


def repo_map(path: str = ".", max_chars: int = 4000) -> dict[str, Any]:
    """Build a compact map of source files and their top-level symbols."""
    try:
        max_chars = int(max_chars)
    except (ValueError, TypeError):
        max_chars = 4000

    root = Path(path).expanduser().resolve()
    if not root.exists():
        return {"error": f"Path not found: {path}"}

    entries: list[str] = []
    total = 0

    def walk(directory: Path) -> None:
        nonlocal total
        try:
            items = sorted(directory.iterdir())
        except PermissionError:
            return
        for item in items:
            if total >= max_chars:
                return
            if item.name.startswith(".") or item.name in _SKIP_DIRS:
                continue
            if item.is_dir():
                walk(item)
            elif item.is_file() and item.suffix in _SOURCE_EXT:
                if item.stat().st_size > 300_000:
                    continue
                try:
                    text = item.read_text("utf-8", errors="replace")
                except Exception:
                    continue
                syms = (_python_symbols(text) if item.suffix == ".py"
                        else _regex_symbols(text, item.suffix))
                rel = item.relative_to(root)
                line = f"{rel}: {', '.join(syms[:12])}" if syms else f"{rel}"
                entries.append(line)
                total += len(line) + 1

    walk(root)
    return {
        "root":      str(root),
        "files":     len(entries),
        "map":       "\n".join(entries)[:max_chars],
        "truncated": total >= max_chars,
    }
