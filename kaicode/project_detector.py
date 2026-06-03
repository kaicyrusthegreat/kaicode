"""Auto-detect project type and relevant context files."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class ProjectInfo(NamedTuple):
    project_type: str
    root: Path
    context_files: list[str]
    description: str


PROJECT_SIGNATURES: list[tuple[str, list[str], str, list[str]]] = [
    # (type, marker_files, description, auto_context_files)
    ("flutter", ["pubspec.yaml", "lib/main.dart"], "Flutter/Dart app",
     ["pubspec.yaml", "lib/main.dart"]),
    ("python_package", ["pyproject.toml", "setup.py"], "Python package",
     ["pyproject.toml", "README.md"]),
    ("python", ["requirements.txt", "*.py"], "Python project",
     ["requirements.txt"]),
    ("node", ["package.json"], "Node.js project",
     ["package.json"]),
    ("react", ["package.json", "src/App.tsx", "src/App.jsx"], "React app",
     ["package.json", "src/App.tsx", "src/App.jsx"]),
    ("nextjs", ["package.json", "next.config.js", "next.config.ts"], "Next.js app",
     ["package.json", "next.config.js"]),
    ("rust", ["Cargo.toml"], "Rust project",
     ["Cargo.toml", "src/main.rs", "src/lib.rs"]),
    ("go", ["go.mod"], "Go module",
     ["go.mod"]),
    ("java_gradle", ["build.gradle", "build.gradle.kts"], "Java/Kotlin Gradle project",
     ["build.gradle", "build.gradle.kts"]),
    ("java_maven", ["pom.xml"], "Java Maven project",
     ["pom.xml"]),
    ("ruby", ["Gemfile"], "Ruby project",
     ["Gemfile"]),
    ("php", ["composer.json"], "PHP project",
     ["composer.json"]),
    ("swift", ["Package.swift", "*.xcodeproj"], "Swift/Xcode project",
     ["Package.swift"]),
    ("elixir", ["mix.exs"], "Elixir/Phoenix project",
     ["mix.exs"]),
    ("django", ["manage.py", "settings.py"], "Django project",
     ["manage.py", "requirements.txt"]),
    ("fastapi", ["main.py", "requirements.txt"], "FastAPI project",
     ["main.py", "requirements.txt"]),
    ("docker", ["Dockerfile", "docker-compose.yml"], "Docker project",
     ["Dockerfile", "docker-compose.yml"]),
    ("terraform", ["*.tf", "main.tf"], "Terraform infrastructure",
     ["main.tf", "variables.tf"]),
]


def detect_project(path: str = ".") -> ProjectInfo:
    """Detect the project type and return relevant context."""
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


def build_system_prompt(project_info: ProjectInfo, extra: str = "") -> str:
    """Build a system prompt incorporating project context."""
    base = f"""You are KaiCode, an expert AI coding assistant running in the terminal.

Project type: {project_info.description}
Working directory: {project_info.root} (this is a directory — never pass it as a file path to tools)

You have access to tools to read files, edit code, search, run commands, and use git.

IMPORTANT: Only call tools when the user asks you to do something with their code or files.
For greetings, questions, or general conversation — respond directly without calling any tools.

When helping with code changes:
1. Always read the file first before editing
2. Show diffs for significant changes
3. Run tests when available after making changes
4. Be precise and make minimal necessary changes
5. Explain what you're doing briefly

Keep responses concise and focused.
"""
    if extra:
        base += f"\n{extra}"
    return base.strip()
