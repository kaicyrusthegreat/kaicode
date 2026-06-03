"""Rich display helpers for KaiCode output rendering."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.align import Align
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.tree import Tree
from rich import box

from kaicode.ui.theme import KAICODE_THEME, ASCII_LOGO, LOGO_COMPACT, KAICODE_VERSION


console = Console(theme=KAICODE_THEME, highlight=False)


_TOOL_ICONS = {
    "read_file":        "○",
    "edit_file":        "◈",
    "create_file":      "◆",
    "create_directory": "▸",
    "list_files":       "▤",
    "search_files":     "⊛",
    "run_command":      "▶",
    "git_status":       "⎇",
    "git_diff":         "⎇",
    "git_commit":       "⊙",
}

_MODEL_LABELS = {
    "model-opus-4-8":           "Most capable",
    "model-sonnet-4-6":         "Balanced performance",
    "model-haiku-4-5-20251001": "Fast & efficient",
    "model-3-5-sonnet-20241022":"Strong reasoning",
    "model-3-5-haiku-20241022": "Fast",
    "gpt-4o":                    "OpenAI flagship",
    "gpt-4-turbo":               "GPT-4 Turbo",
    "gpt-4o-mini":               "Fast & affordable",
    "llama3.2":                  "Local · fast",
    "llama3.1":                  "Local · capable",
    "llama3.1:8b":               "Local · fast",
    "qwen2.5-coder":             "Local · code-focused",
    "mistral-nemo":              "Local · multilingual",
    "deepseek-r1:8b":            "Local · reasoning",
    "gemma4:latest":             "Local · Google",
    "gpt-oss:20b":               "Local · large",
    "llama-3.1-70b-versatile":   "Groq · fast",
    "llama-3.3-70b-versatile":   "Groq · versatile",
    "mixtral-8x7b-32768":        "Groq · large context",
}


def _get_git_branch(cwd: str | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2,
            cwd=cwd or ".",
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch if branch != "HEAD" else ""
    except Exception:
        pass
    return ""


def print_header(model: str, provider: str, cwd: str) -> None:
    cwd_short = str(Path(cwd).resolve())
    home = str(Path.home())
    if cwd_short.startswith(home):
        cwd_short = "~" + cwd_short[len(home):]

    branch = _get_git_branch(cwd)

    header = Text()
    header.append(" ⟨ KaiCode ⟩ ", style="kaicode.logo")
    header.append("  ")
    header.append(provider, style="kaicode.assistant")
    header.append(" / ", style="kaicode.muted")
    header.append(model, style="kaicode.model")
    header.append("  ")
    header.append(cwd_short, style="kaicode.dir")
    if branch:
        header.append("  ")
        header.append(f"({branch})", style="kaicode.branch")
    header.append("  ")
    header.append("by Kai Cyrus", style="kaicode.footer")

    console.rule(header, style="kaicode.separator")


def print_splash() -> None:
    console.print(Align.center(Text(ASCII_LOGO, style="kaicode.logo")))

    tagline = Text()
    tagline.append(f"v{KAICODE_VERSION}", style="kaicode.footer")
    tagline.append("  ·  ", style="kaicode.muted")
    tagline.append("by Kai Cyrus", style="kaicode.footer")
    tagline.append("  ·  ", style="kaicode.muted")
    tagline.append("Multi-provider AI coding assistant", style="kaicode.info")
    console.print(Align.center(tagline))
    console.print()


def print_user_message(content: str) -> None:
    console.print(Text("You", style="kaicode.user"), end=" ")
    console.print(Text("›", style="kaicode.prompt"), end=" ")
    console.print(Text(content))


def render_assistant_chunk(chunk: str) -> None:
    console.print(chunk, end="", markup=False, highlight=False)


def render_assistant_message(content: str) -> None:
    if "```" in content or "`" in content:
        console.print(Markdown(content, code_theme="monokai"))
    else:
        console.print(Text(content))


def print_tool_call(tool_name: str, arguments: dict) -> None:
    icon   = _TOOL_ICONS.get(tool_name, "·")
    detail = _summarize_args(tool_name, arguments)

    line = Text()
    line.append(f"  {icon}  ", style="kaicode.tool_call")
    line.append(tool_name, style="bold kaicode.tool_call")
    if detail:
        line.append("  →  ", style="kaicode.muted")
        line.append(detail, style="kaicode.dir")
    console.print(line)


def _summarize_args(tool_name: str, args: dict) -> str:
    if tool_name in ("read_file", "edit_file", "create_file", "create_directory"):
        return args.get("path", "")
    if tool_name == "run_command":
        cmd = args.get("command", "")
        return ("$ " + cmd)[:70] + ("…" if len(cmd) > 68 else "")
    if tool_name == "search_files":
        return f'"{args.get("pattern","")}" in {args.get("path",".")}'
    if tool_name == "git_commit":
        return f'"{args.get("message","")}"'
    return str(args)[:60]


def print_tool_result(tool_name: str, result: str) -> None:
    import json
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        data = {"output": result}

    if "error" in data:
        console.print(Text(f"  ✗  {data['error']}", style="kaicode.error"))
        return

    if tool_name == "edit_file" and "diff" in data:
        _print_diff(data["diff"])
        return

    if tool_name == "read_file" and "content" in data:
        path = data.get("path", "")
        ext  = Path(path).suffix.lstrip(".")
        console.print(Panel(
            Syntax(data["content"][:3000], ext or "text",
                   theme="friendly", line_numbers=True, word_wrap=True),
            title=f"[kaicode.dir]{path}[/]",
            border_style="kaicode.separator",
            padding=(0, 1),
        ))
        return

    if tool_name == "list_files" and "entries" in data:
        _print_file_tree(data)
        return

    if tool_name == "search_files" and "results" in data:
        _print_search_results(data)
        return

    if tool_name == "git_status" and "branch" in data:
        _print_git_status(data)
        return

    if tool_name == "run_command":
        stdout = data.get("stdout", "").strip()
        stderr = data.get("stderr", "").strip()
        rc     = data.get("returncode", 0)
        if stdout:
            console.print(Panel(
                Text(stdout[:2000]),
                title=f"[kaicode.dir]stdout[/]  [{'kaicode.success' if rc == 0 else 'kaicode.error'}]rc={rc}[/]",
                border_style="kaicode.success" if rc == 0 else "kaicode.error",
                padding=(0, 1),
            ))
        if stderr:
            console.print(Panel(
                Text(stderr[:1000], style="kaicode.warning"),
                title="[kaicode.dir]stderr[/]",
                border_style="kaicode.warning",
                padding=(0, 1),
            ))
        return

    console.print(Text(f"  ✓  {tool_name} done", style="kaicode.tool_result"))


def _print_diff(diff: str) -> None:
    if not diff:
        console.print(Text("  (no changes)", style="kaicode.muted"))
        return
    text = Text()
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            text.append(line + "\n", style="kaicode.diff.add")
        elif line.startswith("-") and not line.startswith("---"):
            text.append(line + "\n", style="kaicode.diff.remove")
        elif line.startswith("@@"):
            text.append(line + "\n", style="kaicode.diff.header")
        else:
            text.append(line + "\n", style="kaicode.dir")
    console.print(Panel(text, title="[kaicode.dir]diff[/]",
                        border_style="kaicode.separator", padding=(0, 1)))


def _print_file_tree(data: dict) -> None:
    tree = Tree(f"[kaicode.file_tree.dir]{data['path']}[/]")
    nodes: dict[str, Any] = {"": tree}
    for entry in data.get("entries", [])[:100]:
        parts      = Path(entry["path"]).parts
        parent_key = str(Path(*parts[:-1])) if len(parts) > 1 else ""
        parent     = nodes.get(parent_key, tree)
        if entry["type"] == "dir":
            label = f"[kaicode.file_tree.dir]{parts[-1]}/[/]"
        else:
            size     = entry.get("size", 0) or 0
            size_str = f" [kaicode.muted]{_human_size(size)}[/]" if size else ""
            label    = f"[kaicode.file_tree.file]{parts[-1]}[/]{size_str}"
        nodes[entry["path"]] = parent.add(label)
    console.print(tree)


def _print_search_results(data: dict) -> None:
    results = data.get("results", [])
    if not results:
        console.print(Text(f"  No results for '{data['pattern']}'", style="kaicode.muted"))
        return
    table = Table(box=box.SIMPLE, show_header=True, header_style="kaicode.assistant")
    table.add_column("File",    style="kaicode.info",  no_wrap=True)
    table.add_column("Line",    style="kaicode.muted", justify="right", width=6)
    table.add_column("Content")
    for r in results[:30]:
        table.add_row(r["file"], str(r["line"]), r["content"][:100])
    if data.get("truncated"):
        console.print(Text(f"  (showing first 30 of {data['total']} results)", style="kaicode.muted"))
    console.print(table)


def _print_git_status(data: dict) -> None:
    line = Text()
    line.append("  Branch  ", style="kaicode.muted")
    line.append(data.get("branch", "unknown"), style="kaicode.branch")
    console.print(line)
    for item in data.get("staged",   []): console.print(Text(f"  + {item['file']}", style="kaicode.diff.add"))
    for item in data.get("unstaged", []): console.print(Text(f"  ~ {item['file']}", style="kaicode.warning"))
    for f    in data.get("untracked",[]): console.print(Text(f"  ? {f}",             style="kaicode.muted"))
    if data.get("clean"):
        console.print(Text("  Working tree clean", style="kaicode.success"))


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size}{unit}"
        size //= 1024
    return f"{size}GB"


def print_status(tokens_used: int, model: str, provider: str, status: str = "ready") -> None:
    bar = Text()
    bar.append(" ◈ ",                    style="kaicode.assistant")
    bar.append(f"{provider}",            style="kaicode.info")
    bar.append(" / ",                    style="kaicode.muted")
    bar.append(f"{model}",               style="kaicode.model")
    bar.append("  ·  ",                  style="kaicode.muted")
    bar.append(f"~{tokens_used:,} tok",  style="kaicode.tokens")
    bar.append("  ·  ",                  style="kaicode.muted")
    bar.append(status,                   style="kaicode.info")
    bar.append("  ·  ",                  style="kaicode.muted")
    bar.append("by Kai Cyrus",           style="kaicode.footer")
    console.rule(bar, style="kaicode.separator")


def print_error(msg: str) -> None:
    console.print(Text(f"  ✗  {msg}", style="kaicode.error"))


def print_info(msg: str) -> None:
    console.print(Text(f"  ·  {msg}", style="kaicode.info"))


def print_success(msg: str) -> None:
    console.print(Text(f"  ✓  {msg}", style="kaicode.success"))


def print_help() -> None:
    table = Table(
        title=" KaiCode Commands ",
        box=box.ROUNDED,
        border_style="kaicode.separator",
        title_style="bold kaicode.logo",
        header_style="kaicode.muted",
        show_lines=False,
        pad_edge=True,
        padding=(0, 1),
    )
    table.add_column("Command",     style="bold kaicode.assistant", width=20)
    table.add_column("Description")

    sections = [
        ("Models & Providers", ""),
        ("/model [name]",    "Switch model — shows picker if no name given"),
        ("/provider [name]", "Switch provider — ollama / openai / openai / groq"),
        ("Sessions", ""),
        ("/save [name]",     "Save current conversation"),
        ("/load <name>",     "Load a saved conversation"),
        ("/sessions",        "List all saved sessions"),
        ("Context & Code", ""),
        ("/diff",            "Show the last applied diff"),
        ("/context",         "Show auto-detected context files"),
        ("Conversation", ""),
        ("/clear",           "Clear conversation history"),
        ("/status",          "Show tokens, model, and provider"),
        ("/help",            "Show this help"),
        ("/quit",            "Exit KaiCode"),
    ]
    for item in sections:
        if item[1] == "":
            table.add_section()
            table.add_row(f"[kaicode.muted italic]{item[0]}[/]", "")
        else:
            table.add_row(item[0], item[1])

    console.print()
    console.print(table)
    console.print()

    perm = Table(
        title=" Tool Permissions ",
        box=box.ROUNDED,
        border_style="kaicode.separator",
        title_style="bold kaicode.tool_call",
        header_style="kaicode.muted",
        padding=(0, 1),
    )
    perm.add_column("Key",    style="bold kaicode.assistant", width=5, justify="center")
    perm.add_column("Action")
    perm.add_row("1", "Yes, do it")
    perm.add_row("2", "No, skip this action")
    perm.add_row("3", "Yes, always allow this tool for the session")
    perm.add_row("4", "Yes, allow all tools for the session")
    console.print(perm)
    console.print()

    console.print(Text("  Tips", style="bold kaicode.assistant"))
    console.print(Text("  ·  Read-only tools (read_file, search, git status) run without asking", style="kaicode.muted"))
    console.print(Text("  ·  Write and execute tools always ask for permission first",            style="kaicode.muted"))
    console.print(Text("  ·  Use /model to switch between local Ollama models and cloud APIs",   style="kaicode.muted"))
    console.print()
