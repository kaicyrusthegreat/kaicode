"""Rich display helpers for KaiCode output rendering."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.tree import Tree
from rich import box

from kaicode.ui.theme import KAICODE_THEME, ASCII_LOGO, LOGO_COMPACT


console = Console(theme=KAICODE_THEME, highlight=False)


def print_header(model: str, provider: str, cwd: str) -> None:
    """Print the KaiCode header bar."""
    cwd_short = str(Path(cwd).resolve())
    home = str(Path.home())
    if cwd_short.startswith(home):
        cwd_short = "~" + cwd_short[len(home):]

    header = Text()
    header.append(" ⟨ KaiCode ⟩ ", style="kaicode.logo")
    header.append("  ")
    header.append(f"[{provider}] ", style="kaicode.assistant")
    header.append(model, style="kaicode.model")
    header.append("  ")
    header.append(cwd_short, style="kaicode.dir")
    header.append("  ")
    header.append("by Kai Cyrus", style="kaicode.footer")

    console.rule(header, style="kaicode.separator")


def print_splash() -> None:
    """Print the splash screen."""
    from rich.align import Align
    logo_text = Text(ASCII_LOGO, style="kaicode.logo")
    console.print(Align.center(logo_text))
    console.print(
        Align.center(Text("by Kai Cyrus  •  Multi-provider AI coding assistant", style="kaicode.footer"))
    )
    console.print()


def print_user_message(content: str) -> None:
    """Print a user message."""
    console.print(Text("You", style="kaicode.user"), end=" ")
    console.print(Text("›", style="kaicode.prompt"), end=" ")
    console.print(Text(content, style="white"))


def render_assistant_chunk(chunk: str) -> None:
    """Print a streaming chunk from the assistant."""
    console.print(chunk, end="", markup=False, highlight=False)


def render_assistant_message(content: str) -> None:
    """Render a complete assistant message with markdown."""
    if _has_code_blocks(content):
        _render_markdown(content)
    else:
        console.print(Text(content, style="white"))


def _has_code_blocks(text: str) -> bool:
    return "```" in text or "`" in text


def _render_markdown(text: str) -> None:
    md = Markdown(text, code_theme="monokai")
    console.print(md)


def print_tool_call(tool_name: str, arguments: dict) -> None:
    """Print a tool call being made."""
    import json
    args_str = json.dumps(arguments, indent=2)
    if len(args_str) > 300:
        args_str = args_str[:300] + "..."

    content = Text()
    content.append(f"  {tool_name}", style="kaicode.tool_call")
    content.append(f"({_summarize_args(tool_name, arguments)})", style="dim white")

    console.print(content)


def _summarize_args(tool_name: str, args: dict) -> str:
    if tool_name in ("read_file", "edit_file", "create_file"):
        return args.get("path", "")
    if tool_name == "run_command":
        cmd = args.get("command", "")
        return cmd[:60] + "..." if len(cmd) > 60 else cmd
    if tool_name == "search_files":
        return f'"{args.get("pattern", "")}" in {args.get("path", ".")}'
    if tool_name == "git_commit":
        return f'"{args.get("message", "")}"'
    return str(args)[:60]


def print_tool_result(tool_name: str, result: str) -> None:
    """Print the result of a tool call."""
    import json
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        data = {"output": result}

    if "error" in data:
        console.print(f"  [kaicode.error]✗ {data['error']}[/]")
        return

    if tool_name == "edit_file" and "diff" in data:
        _print_diff(data["diff"])
        return

    if tool_name == "read_file" and "content" in data:
        path = data.get("path", "")
        ext = Path(path).suffix.lstrip(".")
        syntax = Syntax(
            data["content"][:3000],
            ext or "text",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        console.print(Panel(syntax, title=f"[dim]{path}[/]", border_style="dim cyan", padding=(0, 1)))
        return

    if tool_name == "list_files" and "entries" in data:
        _print_file_tree(data)
        return

    if tool_name == "search_files" and "results" in data:
        _print_search_results(data)
        return

    if tool_name in ("git_status",) and "branch" in data:
        _print_git_status(data)
        return

    if tool_name == "run_command":
        stdout = data.get("stdout", "").strip()
        stderr = data.get("stderr", "").strip()
        rc = data.get("returncode", 0)
        if stdout:
            console.print(Panel(
                Text(stdout[:2000], style="dim white"),
                title=f"[dim]stdout (rc={rc})[/]",
                border_style="dim green" if rc == 0 else "dim red",
                padding=(0, 1),
            ))
        if stderr:
            console.print(Panel(
                Text(stderr[:1000], style="dim yellow"),
                title="[dim]stderr[/]",
                border_style="dim yellow",
                padding=(0, 1),
            ))
        return

    console.print(Text(f"  ✓ {tool_name} completed", style="kaicode.tool_result"))


def _print_diff(diff: str) -> None:
    if not diff:
        console.print(Text("  (no changes)", style="dim"))
        return
    lines = diff.splitlines()
    text = Text()
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            text.append(line + "\n", style="kaicode.diff.add")
        elif line.startswith("-") and not line.startswith("---"):
            text.append(line + "\n", style="kaicode.diff.remove")
        elif line.startswith("@@"):
            text.append(line + "\n", style="kaicode.diff.header")
        else:
            text.append(line + "\n", style="dim white")
    console.print(Panel(text, title="[dim]diff[/]", border_style="dim cyan", padding=(0, 1)))


def _print_file_tree(data: dict) -> None:
    tree = Tree(f"[kaicode.file_tree.dir]{data['path']}[/]")
    nodes: dict[str, Any] = {"": tree}

    for entry in data.get("entries", [])[:100]:
        parts = Path(entry["path"]).parts
        parent_key = str(Path(*parts[:-1])) if len(parts) > 1 else ""
        parent_node = nodes.get(parent_key, tree)

        if entry["type"] == "dir":
            style = "kaicode.file_tree.dir"
            label = f"[{style}]{parts[-1]}/[/]"
        else:
            size = entry.get("size", 0) or 0
            size_str = f" [dim]{_human_size(size)}[/]" if size else ""
            label = f"[kaicode.file_tree.file]{parts[-1]}[/]{size_str}"

        node = parent_node.add(label)
        nodes[entry["path"]] = node

    console.print(tree)


def _print_search_results(data: dict) -> None:
    results = data.get("results", [])
    if not results:
        console.print(Text(f"  No results for '{data['pattern']}'", style="dim"))
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="kaicode.assistant")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", style="dim", justify="right", width=6)
    table.add_column("Content", style="white")

    for r in results[:30]:
        table.add_row(r["file"], str(r["line"]), r["content"][:100])

    if data.get("truncated"):
        console.print(Text(f"  (showing first 30 of {data['total']} results)", style="dim"))
    console.print(table)


def _print_git_status(data: dict) -> None:
    lines = Text()
    lines.append(f"  Branch: ", style="dim")
    lines.append(data.get("branch", "unknown"), style="bold cyan")
    console.print(lines)

    for item in data.get("staged", []):
        console.print(Text(f"  + {item['file']}", style="kaicode.diff.add"))
    for item in data.get("unstaged", []):
        console.print(Text(f"  ~ {item['file']}", style="kaicode.warning"))
    for f in data.get("untracked", []):
        console.print(Text(f"  ? {f}", style="dim"))
    if data.get("clean"):
        console.print(Text("  Working tree clean", style="kaicode.success"))


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size}{unit}"
        size //= 1024
    return f"{size}GB"


def print_status(tokens_used: int, model: str, provider: str, status: str = "ready") -> None:
    """Print the status bar."""
    bar = Text()
    bar.append(" KaiCode ", style="kaicode.logo")
    bar.append("│ ", style="dim")
    bar.append(f"{provider}/{model} ", style="kaicode.model")
    bar.append("│ ", style="dim")
    bar.append(f"~{tokens_used:,} tokens ", style="kaicode.tokens")
    bar.append("│ ", style="dim")
    bar.append(status, style="kaicode.info")
    bar.append(" │ ", style="dim")
    bar.append("by Kai Cyrus", style="kaicode.footer")
    console.rule(bar, style="kaicode.separator")


def print_error(msg: str) -> None:
    console.print(Text(f"✗ {msg}", style="kaicode.error"))


def print_info(msg: str) -> None:
    console.print(Text(f"  {msg}", style="kaicode.info"))


def print_success(msg: str) -> None:
    console.print(Text(f"✓ {msg}", style="kaicode.success"))


def print_help() -> None:
    """Print help text."""
    table = Table(title="KaiCode Commands", box=box.ROUNDED, border_style="cyan")
    table.add_column("Command", style="bold cyan", width=18)
    table.add_column("Description", style="white")

    commands = [
        ("/model [name]", "Switch AI model (shows picker if no name given)"),
        ("/provider [name]", "Switch AI provider"),
        ("/clear", "Clear conversation history"),
        ("/diff", "Show the last applied diff"),
        ("/apply", "Apply the last suggested code change"),
        ("/reject", "Reject the last suggested change"),
        ("/save [name]", "Save current session"),
        ("/load [name]", "Load a saved session"),
        ("/sessions", "List saved sessions"),
        ("/context", "Show files loaded into context"),
        ("/status", "Show current status (tokens, model, etc.)"),
        ("/quit", "Exit KaiCode"),
        ("/help", "Show this help message"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)
    console.print()

    perm_table = Table(title="Tool Permissions", box=box.ROUNDED, border_style="dim cyan")
    perm_table.add_column("Option", style="bold cyan", width=6)
    perm_table.add_column("Meaning", style="white")
    perm_table.add_row("1", "Yes, do it")
    perm_table.add_row("2", "No, skip this action")
    perm_table.add_row("3", "Yes, and always allow this tool type for the session")
    perm_table.add_row("4", "Yes, and allow ALL tools for the session (no more prompts)")
    console.print(perm_table)
    console.print()

    console.print(Text("Tips:", style="bold cyan"))
    console.print(Text("  • Read-only tools (read_file, search, git status) run without asking", style="dim white"))
    console.print(Text("  • Write/execute tools always ask first, like KaiCode", style="dim white"))
    console.print(Text("  • Use /model to switch between local (Ollama) and cloud models", style="dim white"))
    console.print()
