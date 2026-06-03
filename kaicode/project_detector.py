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


def build_system_prompt(project_info: ProjectInfo, extra: str = "") -> str:
    sections: list[str] = []

    sections.append(
        f"You are KaiCode, an AI coding assistant that runs in the terminal and takes real actions using tools.\n\n"
        f"Project: {project_info.description}\n"
        f"Working directory: {project_info.root}"
    )

    # Inject actual file contents for key project files
    file_sections = []
    for rel_path in project_info.context_files[:4]:        # max 4 files
        abs_path = project_info.root / rel_path
        if abs_path.is_file():
            content = _read_file_snippet(abs_path, max_chars=800)   # 800 not 1500
            if content:
                file_sections.append(f"### {rel_path}\n```\n{content}\n```")
    if file_sections:
        sections.append("## Project files\n" + "\n\n".join(file_sections))

    # Inject git context
    git_ctx = _git_context(project_info.root)
    if git_ctx:
        sections.append(f"## Git context\n{git_ctx}")

    # Inject persistent memory from previous sessions
    memory = read_memory(str(project_info.root))
    if memory.strip():
        sections.append(f"## Your memory from previous sessions\n{memory.strip()}")

    sections.append("""## Your tools
- read_file — read any file
- edit_file — edit a file by replacing text
- create_file — create a new file with content
- create_directory — create a folder/directory at any path
- list_files — list files in a directory
- search_files — search for patterns in files
- run_command — run any shell command
- git_status / git_commit — git operations
- grep_ast — find function/class definitions by name (smarter than text search)
- repo_map — compact map of the whole codebase (files + their classes/functions)
- web_fetch — fetch a URL for docs or API references
- run_tests — run the project's test suite (auto-detected)
- update_memory — save notes that persist across sessions

## Rules
1. When the user asks you to DO something — use the appropriate tool. Do NOT say you cannot do it.
2. For tasks involving 2+ steps or file edits: briefly outline your plan first (a short numbered list), THEN call the first tool. This gives the user a chance to confirm.
3. For simple single-step tasks (create one file, run one command): just do it immediately with no preamble.
4. Always read a file before editing it.
5. You CAN create files and directories anywhere on the filesystem.
6. Keep explanations concise. Let tool output speak for itself.
7. For greetings and pure concept questions — respond directly without tools.
8. Use update_memory to save anything worth remembering across sessions.""")

    if extra:
        sections.append(extra)

    return "\n\n".join(sections)
