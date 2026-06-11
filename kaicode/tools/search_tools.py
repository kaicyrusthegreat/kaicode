"""Search tools for the KaiCode agent."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def search_files(
    pattern: str,
    path: str = ".",
    file_pattern: str = "*",
    case_sensitive: bool = False,
    max_results: int = 50,
    use_regex: bool = False,
) -> dict[str, Any]:
    """Search for a pattern in files."""
    try:
        max_results    = int(max_results)
        case_sensitive = str(case_sensitive).lower() not in ("false", "0", "")
        use_regex      = str(use_regex).lower() not in ("false", "0", "")
        root = Path(path).expanduser().resolve()
        if not root.exists():
            return {"error": f"Path not found: {path}"}

        flags = 0 if case_sensitive else re.IGNORECASE
        if use_regex:
            try:
                compiled = re.compile(pattern, flags)
            except re.error as e:
                return {"error": f"Invalid regex: {e}"}
        else:
            compiled = re.compile(re.escape(pattern), flags)

        SKIP_DIRS = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            "dist", "build", ".eggs",
            # Vendored / generated trees — searching them surfaces dependency
            # source (e.g. ios/Pods/**.h) as if it were project code.
            "Pods", "Carthage", "DerivedData", "vendor", "target", "coverage",
        }
        SKIP_EXTENSIONS = {
            ".pyc", ".pyo", ".class", ".o", ".so", ".dylib",
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
            ".zip", ".tar", ".gz", ".bin", ".exe",
        }

        results = []

        def search_dir(directory: Path) -> None:
            try:
                for item in sorted(directory.iterdir()):
                    if item.name.startswith(".") and item.name not in {".env"}:
                        continue
                    if item.is_dir():
                        if item.name not in SKIP_DIRS:
                            search_dir(item)
                    elif item.is_file():
                        if item.suffix in SKIP_EXTENSIONS:
                            continue
                        if file_pattern != "*" and not item.match(file_pattern):
                            continue
                        if len(results) >= max_results:
                            return
                        try:
                            _search_file(item, root, compiled, results, max_results)
                        except (PermissionError, UnicodeDecodeError):
                            pass
            except PermissionError:
                pass

        search_dir(root)

        return {
            "pattern": pattern,
            "path": str(root),
            "results": results,
            "total": len(results),
            "truncated": len(results) >= max_results,
        }
    except Exception as e:
        return {"error": str(e)}


def _search_file(
    file_path: Path,
    root: Path,
    pattern: re.Pattern,
    results: list,
    max_results: int,
) -> None:
    if file_path.stat().st_size > 500_000:
        return

    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    for lineno, line in enumerate(lines, 1):
        if len(results) >= max_results:
            break
        if pattern.search(line):
            results.append({
                "file": str(file_path.relative_to(root)),
                "line": lineno,
                "content": line.strip(),
            })
