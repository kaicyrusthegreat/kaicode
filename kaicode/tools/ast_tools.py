"""AST-based symbol search — finds definitions, not just text matches."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


_SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".eggs"}


def _py_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [a.arg for a in node.args.args]
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)})"


def _search_python(file_path: Path, root: Path, symbol: str, symbol_type: str) -> list[dict]:
    try:
        tree = ast.parse(file_path.read_text("utf-8", errors="replace"))
    except SyntaxError:
        return []
    hits = []
    sym_lower = symbol.lower()
    for node in ast.walk(tree):
        if symbol_type in ("any", "function") and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if sym_lower in node.name.lower():
                hits.append({
                    "file": str(file_path.relative_to(root)),
                    "line": node.lineno,
                    "type": "function",
                    "name": node.name,
                    "signature": _py_signature(node),
                })
        elif symbol_type in ("any", "class") and isinstance(node, ast.ClassDef):
            if sym_lower in node.name.lower():
                hits.append({
                    "file": str(file_path.relative_to(root)),
                    "line": node.lineno,
                    "type": "class",
                    "name": node.name,
                })
    return hits


_LANG_PATTERNS: dict[str, list[str]] = {
    ".js":   [r'\b(?:function|const|let|var|class)\s+({sym})\b', r'\b({sym})\s*[:=]\s*(?:function|\()'],
    ".ts":   [r'\b(?:function|const|let|var|class|interface|type)\s+({sym})\b'],
    ".tsx":  [r'\b(?:function|const|class)\s+({sym})\b'],
    ".dart": [r'\b\w+\s+({sym})\s*[({]', r'\bclass\s+({sym})\b'],
    ".go":   [r'\bfunc\s+(?:\([^)]+\)\s*)?({sym})\b', r'\btype\s+({sym})\b'],
    ".rs":   [r'\b(?:fn|struct|enum|trait|impl)\s+({sym})\b'],
    ".java": [r'\b(?:class|interface|void|public|private|protected)\s+({sym})\b'],
    ".kt":   [r'\b(?:fun|class|object|interface)\s+({sym})\b'],
    ".rb":   [r'\bdef\s+({sym})\b', r'\bclass\s+({sym})\b'],
    ".swift":[r'\b(?:func|class|struct|enum)\s+({sym})\b'],
}


def _search_regex(file_path: Path, root: Path, symbol: str) -> list[dict]:
    pats = _LANG_PATTERNS.get(file_path.suffix.lower(), [])
    if not pats:
        return []
    compiled = [re.compile(p.replace("{sym}", re.escape(symbol)), re.I) for p in pats]
    try:
        lines = file_path.read_text("utf-8", errors="replace").splitlines()
    except Exception:
        return []
    hits = []
    for lineno, line in enumerate(lines, 1):
        for pat in compiled:
            if pat.search(line):
                hits.append({
                    "file": str(file_path.relative_to(root)),
                    "line": lineno,
                    "type": "definition",
                    "name": symbol,
                    "content": line.strip()[:120],
                })
                break
    return hits


def grep_ast(
    symbol: str,
    path: str = ".",
    symbol_type: str = "any",
) -> dict[str, Any]:
    """Search for symbol definitions by name using AST (Python) or regex (other languages)."""
    symbol_type = str(symbol_type).lower()
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return {"error": f"Path not found: {path}"}

    results: list[dict] = []

    def walk(directory: Path) -> None:
        if len(results) >= 30:
            return
        try:
            for item in sorted(directory.iterdir()):
                if item.name in _SKIP or item.name.startswith("."):
                    continue
                if item.is_dir():
                    walk(item)
                elif item.is_file():
                    if item.suffix == ".py":
                        results.extend(_search_python(item, root, symbol, symbol_type))
                    elif item.suffix in _LANG_PATTERNS:
                        results.extend(_search_regex(item, root, symbol))
                    if len(results) >= 30:
                        return
        except PermissionError:
            pass

    walk(root)
    return {
        "symbol":  symbol,
        "type":    symbol_type,
        "results": results[:30],
        "total":   len(results),
    }
