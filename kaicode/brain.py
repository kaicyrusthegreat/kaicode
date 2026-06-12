"""Project Brain — automatic repository indexing and knowledge mapping."""

import ast
import os
from pathlib import Path
from rich.console import Console

from kaicode.ui.display import print_info, print_success


def _extract_symbols(file_path: Path) -> list[str]:
    """Parse python file and return top level classes and functions."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        symbols = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols.append(f"Class: {node.name}")
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                symbols.append(f"Function: {node.name}")
        return symbols
    except Exception:
        return []


def build_project_brain(cwd: str) -> None:
    """Scan the repository and build a knowledge graph (PROJECT_BRAIN.md)."""
    print_info("Scanning project to build Project Brain...")

    root = Path(cwd)
    ignore_dirs = {
        ".git",
        "__pycache__",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
    }

    brain_content = ["# Project Brain Knowledge Graph\n"]
    brain_content.append("Auto-generated directory of key architectural symbols.\n")

    symbol_count = 0
    file_count = 0

    for curr_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

        for file in files:
            if file.endswith(".py"):
                file_count += 1
                full_path = Path(curr_root) / file
                rel_path = full_path.relative_to(root)

                symbols = _extract_symbols(full_path)
                if symbols:
                    brain_content.append(f"## {rel_path}")
                    for sym in symbols:
                        brain_content.append(f"- {sym}")
                        symbol_count += 1
                    brain_content.append("")

    target = root / "PROJECT_BRAIN.md"
    target.write_text("\n".join(brain_content), encoding="utf-8")
    print_success(
        f"Project Brain generated: {symbol_count} symbols across {file_count} Python files."
    )
    print_info(f"Saved to {target.name}")
