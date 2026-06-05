"""Auto-detect project type and relevant context files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple

from kaicode.tools.memory_tools import read_memory


class ProjectInfo(NamedTuple):
    project_type: str
    root: Path
    context_files: list[str]
    description: str


PROJECT_SIGNATURES: list[tuple[str, list[str], str, list[str]]] = [
    ("flutter",      ["pubspec.yaml", "lib/main.dart"],              "Flutter/Dart app",
     ["pubspec.yaml", "lib/main.dart"]),
    ("python_package",["pyproject.toml", "setup.py"],               "Python package",
     ["pyproject.toml", "README.md"]),
    ("python",       ["requirements.txt", "*.py"],                   "Python project",
     ["requirements.txt"]),
    ("node",         ["package.json"],                               "Node.js project",
     ["package.json"]),
    ("react",        ["package.json", "src/App.tsx", "src/App.jsx"], "React app",
     ["package.json", "src/App.tsx", "src/App.jsx"]),
    ("nextjs",       ["package.json", "next.config.js", "next.config.ts"], "Next.js app",
     ["package.json", "next.config.js"]),
    ("rust",         ["Cargo.toml"],                                 "Rust project",
     ["Cargo.toml", "src/main.rs", "src/lib.rs"]),
    ("go",           ["go.mod"],                                     "Go module",
     ["go.mod"]),
    ("java_gradle",  ["build.gradle", "build.gradle.kts"],           "Java/Kotlin Gradle project",
     ["build.gradle", "build.gradle.kts"]),
    ("java_maven",   ["pom.xml"],                                    "Java Maven project",
     ["pom.xml"]),
    ("ruby",         ["Gemfile"],                                    "Ruby project",
     ["Gemfile"]),
    ("php",          ["composer.json"],                              "PHP project",
     ["composer.json"]),
    ("swift",        ["Package.swift", "*.xcodeproj"],               "Swift/Xcode project",
     ["Package.swift"]),
    ("elixir",       ["mix.exs"],                                    "Elixir/Phoenix project",
     ["mix.exs"]),
    ("django",       ["manage.py", "settings.py"],                   "Django project",
     ["manage.py", "requirements.txt"]),
    ("fastapi",      ["main.py", "requirements.txt"],                "FastAPI project",
     ["main.py", "requirements.txt"]),
    ("docker",       ["Dockerfile", "docker-compose.yml"],           "Docker project",
     ["Dockerfile", "docker-compose.yml"]),
    ("terraform",    ["*.tf", "main.tf"],                            "Terraform infrastructure",
     ["main.tf", "variables.tf"]),
]


def detect_project(path: str = ".") -> ProjectInfo:
    root = Path(path).expanduser().resolve()
    for ptype, markers, desc, ctx_patterns in PROJECT_SIGNATURES:
        if _matches_markers(root, markers):
            context_files = _resolve_context_files(root, ctx_patterns)
            return ProjectInfo(ptype, root, context_files, desc)
    return ProjectInfo("generic", root, [], "Unknown project")


def _matches_markers(root: Path, markers: list[str]) -> bool:
    for marker in markers:
        if "*" in marker:
            if any(root.glob(marker)):
                return True
        elif (root / marker).exists():
            return True
    return False


def _resolve_context_files(root: Path, patterns: list[str]) -> list[str]:
    resolved = []
    for pattern in patterns:
        if "*" in pattern:
            matches = list(root.glob(pattern))[:2]
            resolved.extend(str(m.relative_to(root)) for m in matches)
        else:
            p = root / pattern
            if p.exists():
                resolved.append(pattern)
    return resolved


def _read_file_snippet(path: Path, max_chars: int = 1500) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + f"\n… (truncated, {len(text)} chars total)"
        return text
    except Exception:
        return ""


def _git_context(root: Path) -> str:
    lines = []
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=3,
        )
        if branch.returncode == 0:
            lines.append(f"Branch: {branch.stdout.strip()}")

        log = subprocess.run(
            ["git", "log", "--oneline", "-8"],
            cwd=root, capture_output=True, text=True, timeout=3,
        )
        if log.returncode == 0 and log.stdout.strip():
            lines.append("Recent commits:\n" + log.stdout.strip())

        diff = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=3,
        )
        if diff.returncode == 0 and diff.stdout.strip():
            lines.append("Uncommitted changes:\n" + diff.stdout.strip()[:600])
    except Exception:
        pass
    return "\n".join(lines)


def _git_context_slim(root: Path) -> str:
    """Minimal git context — just branch + last 4 commits, no diff."""
    lines = []
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=2,
        )
        if branch.returncode == 0:
            lines.append(f"Branch: {branch.stdout.strip()}")

        log = subprocess.run(
            ["git", "log", "--oneline", "-4"],
            cwd=root, capture_output=True, text=True, timeout=2,
        )
        if log.returncode == 0 and log.stdout.strip():
            lines.append(log.stdout.strip())
    except Exception:
        pass
    return "\n".join(lines)


# Project-instruction files, in precedence order. KaiCode reads its own first,
# then stays compatible with KaiCode (AGENTS.md) and the open AGENTS.md
# standard — so a repo set up for any of those Just Works here too.
INSTRUCTION_FILES = ["KAICODE.md", "AGENTS.md", "AGENTS.md", ".kaicoderules"]


def load_instructions(root: Path) -> str:
    """Collect persistent instructions: global (~/.kaicode/KAICODE.md) + the
    first project instruction file found by precedence. Returns a formatted
    block ready to fold into the system prompt (empty string if none)."""
    chunks: list[str] = []

    global_file = Path.home() / ".kaicode" / "KAICODE.md"
    try:
        if global_file.is_file():
            text = global_file.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                chunks.append(f"### Global (~/.kaicode/KAICODE.md)\n{text[:4000]}")
    except Exception:
        pass

    for name in INSTRUCTION_FILES:
        p = root / name
        try:
            if p.is_file():
                text = p.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    chunks.append(f"### {name}\n{text[:8000]}")
                    break   # highest-precedence project file wins
        except Exception:
            continue

    return "\n\n".join(chunks)


def build_system_prompt(project_info: ProjectInfo, extra: str = "", model: str = "") -> str:
    sections: list[str] = []

    sections.append(
        f"You are KaiCode, an AI coding assistant that runs in the terminal and takes real actions using tools.\n\n"
        f"Project: {project_info.description}\n"
        f"Working directory: {project_info.root}"
    )

    # Inject key project file names (NOT full contents — use read_file when needed)
    if project_info.context_files:
        file_list = ", ".join(project_info.context_files[:3])
        sections.append(f"Key files: {file_list}")

    # Inject git context (minimal — just branch + last 4 commits)
    git_ctx = _git_context_slim(project_info.root)
    if git_ctx:
        sections.append(f"## Git\n{git_ctx}")

    # Inject persistent memory from previous sessions (capped)
    memory = read_memory(str(project_info.root))
    if memory.strip():
        mem = memory.strip()[:500]
        sections.append(f"## Memory\n{mem}")

    # Inject project instructions (KAICODE.md / AGENTS.md / AGENTS.md). These are
    # authoritative — the user's own standing orders for this repo.
    instructions = load_instructions(project_info.root)
    if instructions:
        sections.append(
            "## Project Instructions\n"
            "Follow these standing instructions for this project — they override "
            "general defaults:\n\n" + instructions
        )

    sections.append("""## Rules
1. COMPLETE THE WHOLE TASK using tools. Never ask "shall I continue?" — just do it.
2. create_file: put COMPLETE content in ONE call. Never create empty then edit.
3. Always read_file before edit_file. Match old_content exactly.
4. After writing code, run it or run_tests to verify. Fix failures automatically.
5. Keep prose minimal. End with a one-line summary.
6. For greetings (hi, hello, hey) — reply with SHORT text, NO tools.
7. NEVER use type_text/key_press/mouse_click/screenshot unless user explicitly asks for automation.
8. Use update_memory for important notes across sessions.""")

    # Per-model tuning hints
    model_lower = model.lower()
    if "qwen3" in model_lower:
        sections.append(
            "## Model-specific note\n"
            "You are a Qwen3 model. Use /no_think when the task is simple and "
            "does not require deep reasoning. Always use the native tool-calling "
            "mechanism — never output JSON tool calls as plain text."
        )
    elif "phi4" in model_lower:
        sections.append(
            "## Model-specific note\n"
            "You are Phi-4. Think step-by-step before using tools. "
            "Use the native tool-calling mechanism for all tool invocations."
        )
    elif "gemma" in model_lower:
        sections.append(
            "## Model-specific note\n"
            "You are a Gemma model. Be concise and action-oriented. "
            "Use the native tool-calling mechanism — never output tool calls as text."
        )
    elif "granite" in model_lower:
        sections.append(
            "## Model-specific note\n"
            "You are IBM Granite. Focus on precision and correctness. "
            "Use the native tool-calling mechanism for all tool invocations."
        )

    if extra:
        sections.append(extra)

    return "\n\n".join(sections)

