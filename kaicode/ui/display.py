"""Rich display helpers for KaiCode output rendering."""

from __future__ import annotations

import difflib
import re
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

from kaicode.ui.theme import (
    KAICODE_THEME, ASCII_LOGO, LOGO_COMPACT, KAICODE_VERSION, LOGO_GRADIENT,
)


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
    "web_fetch":        "⊕",
    "web_search":       "⊗",
    "type_text":        "⌨",
    "key_press":        "⌨",
    "mouse_click":      "◉",
    "screenshot":       "◧",
    "run_tests":        "⊘",
    "grep_ast":         "⊛",
    "repo_map":         "▤",
}

_MODEL_LABELS = {
    # CyruSagO (self-improving — learns from every turn)
    "cyrusago":                   "Self-improving core — recalls past lessons, learns from each turn (experimental)",
    # OpenAI
    "model-opus-4-8":            "Best for complex reasoning, architecture planning, and large codebases",
    "model-sonnet-4-6":          "Best for everyday coding — smart, fast, well-balanced",
    "model-haiku-4-5-20251001":  "Best for quick edits, simple tasks, and fast responses",
    "model-3-5-sonnet-20241022": "Best for strong reasoning and reliable code generation",
    "model-3-5-haiku-20241022":  "Best for rapid, lightweight coding tasks",
    # OpenAI
    "gpt-4o":                     "Best for complex coding, vision, and multi-step instructions",
    "gpt-4-turbo":                "Best for long documents and context-heavy tasks",
    "gpt-4o-mini":                "Best for fast, affordable day-to-day tasks",
    # Ollama (local)
    "llama3.2":                   "Quick chat, simple tasks — fast, 2 GB ⭐ tool-calling",
    "llama3.2:latest":            "Quick chat, simple tasks — fast, 2 GB ⭐ tool-calling",
    "llama3.1":                   "Coding and longer reasoning — capable, 4.9 GB ⭐ tool-calling",
    "llama3.1:8b":                "Coding and longer reasoning — capable, 4.9 GB ⭐ tool-calling",
    "deepseek-r1:8b":             "Step-by-step reasoning, math, and logic — 5.2 GB",
    "deepseek-r1:latest":         "Step-by-step reasoning, math, and logic",
    "gemma4:latest":              "Google's latest — general tasks, 9.6 GB ⭐ tool-calling",
    "gemma4":                     "Google's latest — general tasks, 9.6 GB ⭐ tool-calling",
    "gemma3:4b":                  "Fast general tasks — compact Google model, 3.3 GB ⭐ tool-calling",
    "gpt-oss:20b":                "Complex coding — large local model, 13 GB (text-only tools)",
    "qwen2.5-coder:7b":           "Code-specialized — generation + completion, 4.7 GB ⭐ tool-calling",
    "qwen2.5-coder":              "Code-specialized — generation + completion ⭐ tool-calling",
    "qwen2.5-coder:latest":       "Code-specialized — generation + completion ⭐ tool-calling",
    "qwen3:4b":                   "Balanced + reasoning — fast Qwen3 model, 2.5 GB ⭐ tool-calling",
    "qwen3:8b":                   "Strong reasoning + coding — Qwen3 model, 5.2 GB ⭐ tool-calling",
    "qwen3-coder:latest":         "Advanced coding tasks — Qwen3 code model, 18 GB",
    "qwen3-coder":                "Advanced coding tasks — Qwen3 code model, 18 GB",
    "devstral:latest":            "Agentic coding, tool use, complex tasks — 14 GB",
    "devstral":                   "Agentic coding, tool use, complex tasks — 14 GB",
    "phi4:latest":                "Reasoning + math — Microsoft, 9.1 GB (text-only tools)",
    "phi4":                       "Reasoning + math — Microsoft, 9.1 GB (text-only tools)",
    "granite4:3b":                "IBM Granite — precision + correctness, 2.1 GB ⭐ tool-calling",
    "granite4":                   "IBM Granite — precision + correctness ⭐ tool-calling",
    "mistral-nemo":               "Multilingual + general use — runs locally",
    "mistral-nemo:latest":        "Multilingual + general use — runs locally",
    # Groq (fast cloud inference)
    "llama-3.1-70b-versatile":   "Powerful reasoning at blazing cloud speed",
    "llama-3.3-70b-versatile":   "Versatile tasks at very high speed (cloud)",
    "mixtral-8x7b-32768":        "Long-context tasks up to 32K tokens (cloud)",
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
    header.append(" ◆ ", style="kaicode.logo")
    header.append("KaiCode", style="kaicode.bubble.kai.name")
    header.append("  ·  ", style="kaicode.muted")
    header.append(provider, style="kaicode.assistant")
    header.append(" / ", style="kaicode.muted")
    header.append(model, style="kaicode.model")
    header.append("  ·  ", style="kaicode.muted")
    header.append(cwd_short, style="kaicode.dir")
    if branch:
        header.append("  ", style="kaicode.muted")
        header.append(f"({branch})", style="kaicode.branch")

    console.rule(header, style="kaicode.separator")


def print_splash() -> None:
    # Block logo rendered with a vertical blue→teal gradient (one color per row).
    rows = [ln for ln in ASCII_LOGO.split("\n") if ln.strip("\r")]
    logo = Text(justify="center")
    last = len(rows) - 1
    for i, row in enumerate(rows):
        color = LOGO_GRADIENT[min(i, len(LOGO_GRADIENT) - 1)]
        logo.append(row + ("\n" if i < last else ""), style=f"bold {color}")
    console.print()
    console.print(Align.center(logo))

    # Framed tagline: a divider rule the width of the logo, then the meta line.
    width = min(max((len(r) for r in rows), default=40), 54)
    console.print(Align.center(Text("─" * width, style="kaicode.separator")))

    tagline = Text(justify="center")
    tagline.append(f"v{KAICODE_VERSION}", style="kaicode.footer")
    tagline.append("  ·  ", style="kaicode.muted")
    tagline.append("Multi-provider AI coding assistant", style="kaicode.assistant")
    tagline.append("  ·  ", style="kaicode.muted")
    tagline.append("by Kai Cyrus", style="kaicode.footer")
    console.print(Align.center(tagline))
    console.print()


def print_user_message(content: str) -> None:
    # Leading blank only — each bubble brings its own gap, so panels are
    # always separated by exactly one blank line, never two.
    console.print()
    console.print(Panel(
        Text(content, style="kaicode.msg.user"),
        box=box.ROUNDED,
        title="[kaicode.bubble.user]◇[/] [kaicode.bubble.user.name]You[/]",
        title_align="left",
        border_style="kaicode.bubble.user",
        padding=(0, 2),
    ))


def print_plan(content: str) -> None:
    """Show the model's plan before tool execution — amber chip bubble."""
    renderable = Markdown(content, code_theme="monokai") if ("```" in content or "`" in content) else Text(content, style="kaicode.msg.plan")
    console.print()
    console.print(Panel(
        renderable,
        box=box.ROUNDED,
        title="[kaicode.bubble.plan]◆[/] [kaicode.bubble.plan.name]Plan[/]",
        title_align="left",
        border_style="kaicode.bubble.plan",
        padding=(1, 2),
    ))


def print_kai_message(content: str) -> None:
    renderable = Markdown(content, code_theme="monokai") if ("```" in content or "`" in content) else Text(content, style="kaicode.msg.kai")
    console.print()
    console.print(Panel(
        renderable,
        box=box.ROUNDED,
        title="[kaicode.bubble.kai]◆[/] [kaicode.bubble.kai.name]KaiCode[/]",
        title_align="left",
        border_style="kaicode.bubble.kai",
        padding=(1, 2),
    ))


def render_assistant_chunk(chunk: str) -> None:
    console.print(chunk, end="", markup=False, highlight=False)


def render_assistant_message(content: str) -> None:
    print_kai_message(content)


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
        # The full diff was already shown as a pre-approval preview, so here we
        # only confirm what landed — avoids printing the same diff twice.
        adds, dels = _diff_stat(data["diff"])
        console.print(Text(f"  ✓  applied  (+{adds} / -{dels})", style="kaicode.success"))
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

    if tool_name == "run_tests" and "output" in data:
        passed = data.get("passed", False)
        rc     = data.get("returncode", -1)
        console.print(Panel(
            Text(data["output"][:4000]),
            title=f"[kaicode.dir]{data.get('command','tests')}[/]  [{'kaicode.success' if passed else 'kaicode.error'}]{'PASSED' if passed else 'FAILED'}[/]",
            border_style="kaicode.success" if passed else "kaicode.error",
            padding=(0, 1),
        ))
        return

    if tool_name == "grep_ast" and "results" in data:
        results = data.get("results", [])
        if not results:
            console.print(Text(f"  No definitions found for '{data.get('symbol','')}'", style="kaicode.muted"))
            return
        table = Table(box=box.SIMPLE, show_header=True, header_style="kaicode.assistant")
        table.add_column("File",    style="kaicode.info", no_wrap=True)
        table.add_column("Line",    style="kaicode.muted", justify="right", width=6)
        table.add_column("Type",    style="kaicode.branch", width=10)
        table.add_column("Signature", style="default")
        for r in results[:20]:
            table.add_row(r["file"], str(r["line"]), r.get("type",""), r.get("signature") or r.get("content",""))
        console.print(table)
        return

    if tool_name == "repo_map" and "map" in data:
        console.print(Panel(
            Text(data["map"][:4000], style="kaicode.dir"),
            title=f"[kaicode.dir]repo map · {data.get('files', 0)} files[/]",
            border_style="kaicode.separator",
            padding=(0, 1),
        ))
        return

    if tool_name == "web_fetch" and "content" in data:
        console.print(Panel(
            Text(data["content"][:3000]),
            title=f"[kaicode.dir]{data.get('url','')[:80]}[/]",
            border_style="kaicode.separator",
            padding=(0, 1),
        ))
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


def _diff_stat(diff: str) -> tuple[int, int]:
    """Count added / removed lines in a unified diff (ignoring file headers)."""
    adds = sum(1 for ln in diff.splitlines()
               if ln.startswith("+") and not ln.startswith("+++"))
    dels = sum(1 for ln in diff.splitlines()
               if ln.startswith("-") and not ln.startswith("---"))
    return adds, dels


def _print_diff(diff: str, title: str = "diff",
                border: str = "kaicode.separator") -> None:
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
    console.print(Panel(text, title=f"[kaicode.dir]{title}[/]",
                        border_style=border, padding=(0, 1)))


# Full-width background tints for the line-by-line diff (KaiCode style).
_DIFF_ADD_BG = "on #14351f"
_DIFF_DEL_BG = "on #3a1717"


def _diff_width() -> int:
    try:
        return min(console.size.width - 2, 140)
    except Exception:
        return 100


def _emit_diff_line(out: Text, lineno: str, marker: str, content: str,
                    bg: str, marker_style: str, width: int) -> None:
    """Append one diff row with a full-width background tint."""
    out.append(f"{lineno:>5} ", style=f"{bg} kaicode.muted")
    out.append(marker, style=f"{bg} {marker_style}")
    out.append(content, style=bg)
    pad = width - (6 + len(marker) + len(content))
    if pad > 0:
        out.append(" " * pad, style=bg)
    out.append("\n")


def _render_diff_body(diff: str) -> Text:
    """Render a unified diff with line numbers and red/green row backgrounds."""
    width = _diff_width()
    out = Text()
    old_ln = new_ln = 0
    for raw in diff.splitlines():
        if raw.startswith(("+++", "---")):
            continue
        if raw.startswith("@@"):
            m = re.search(r"-(\d+)(?:,\d+)? \+(\d+)", raw)
            if m:
                old_ln, new_ln = int(m.group(1)), int(m.group(2))
            if out.plain:                      # blank gap between hunks
                out.append("\n")
            continue
        if raw.startswith("+"):
            _emit_diff_line(out, str(new_ln), "+ ", raw[1:],
                            _DIFF_ADD_BG, "bold green", width)
            new_ln += 1
        elif raw.startswith("-"):
            _emit_diff_line(out, str(old_ln), "- ", raw[1:],
                            _DIFF_DEL_BG, "bold red", width)
            old_ln += 1
        else:
            content = raw[1:] if raw.startswith(" ") else raw
            out.append(f"{new_ln:>5} ", style="kaicode.muted")
            out.append("  ", style="kaicode.muted")
            out.append(content + "\n", style="kaicode.dir")
            old_ln += 1
            new_ln += 1
    return out


def _print_change_header(verb: str, path: str, adds: int, dels: int) -> None:
    head = Text()
    head.append(verb, style="bold kaicode.assistant")
    head.append(f"({path})", style="kaicode.dir")
    console.print()
    console.print(head)

    parts: list[str] = []
    if adds:
        parts.append(f"Added {adds} line" + ("s" if adds != 1 else ""))
    if dels:
        parts.append(f"removed {dels} line" + ("s" if dels != 1 else ""))
    summary = Text("  ⎿ ", style="kaicode.muted")
    summary.append(", ".join(parts) if parts else "no changes", style="kaicode.muted")
    console.print(summary)


def print_change_preview(tool_name: str, args: dict, cwd: str) -> bool:
    """Show what a write tool *would* do, before the permission prompt — the diff
    for an edit, or the new contents for a create. Mirrors KaiCode's
    review-before-apply flow. Returns True if a preview was rendered."""
    if tool_name == "edit_file":
        path = args.get("path", "")
        old  = args.get("old_content", "")
        new  = args.get("new_content", "")
        p = (Path(cwd) / path).expanduser()
        try:
            original = p.read_text("utf-8", errors="replace")
        except Exception:
            return False  # file unreadable — permission panel still shown
        if old and old not in original:
            console.print(Text(
                f"  !  old_content not found in {path} — this edit will fail",
                style="kaicode.warning"))
            return False
        updated = original.replace(old, new, 1)
        diff = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{p.name}", tofile=f"b/{p.name}", n=3,
        ))
        adds, dels = _diff_stat(diff)
        _print_change_header("Update", path, adds, dels)
        console.print(_render_diff_body(diff))
        return True

    if tool_name == "create_file":
        path    = args.get("path", "")
        content = args.get("content", "")
        lines   = content.splitlines()
        exists  = (Path(cwd) / path).expanduser().exists()
        _print_change_header("Overwrite" if exists else "Create",
                             path, len(lines), 0)
        width = _diff_width()
        out = Text()
        for i, line in enumerate(lines[:200], 1):
            _emit_diff_line(out, str(i), "+ ", line,
                            _DIFF_ADD_BG, "bold green", width)
        if len(lines) > 200:
            out.append(f"      … {len(lines) - 200} more lines\n",
                       style="kaicode.muted")
        console.print(out)
        return True

    return False


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
    table.add_column("Command",     style="kaicode.assistant", width=20)
    table.add_column("Description")

    sections = [
        ("Models & Providers", ""),
        ("/model [name]",    "Switch model — shows picker if no name given"),
        ("/provider [name]", "Switch provider — ollama / openai / openai / groq"),
        ("Project & Code", ""),
        ("/init [--force]",  "Generate a KAICODE.md with project instructions"),
        ("/commit",          "AI-generated commit message for current changes"),
        ("/diff",            "Show the last applied diff"),
        ("/context",         "Show auto-detected context files"),
        ("/memory",          "Show project memory (use /memory clear to reset)"),
        ("Safety & History", ""),
        ("/undo",            "Revert the last file change the agent made"),
        ("/redo",            "Re-apply the last undone change"),
        ("/changes",         "List file changes made this session"),
        ("Sessions", ""),
        ("/save [name]",     "Save current conversation"),
        ("/load <name>",     "Load a saved conversation"),
        ("/sessions",        "List all saved sessions"),
        ("Conversation", ""),
        ("/clear",           "Clear conversation history"),
        ("/status",          "Show tokens, cost, model, and provider"),
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
    perm.add_column("Key",    style="kaicode.assistant", width=5, justify="center")
    perm.add_column("Action")
    perm.add_row("1", "Yes, do it")
    perm.add_row("2", "No, skip this action")
    perm.add_row("3", "Yes, always allow this tool for the session")
    perm.add_row("4", "Yes, allow all tools for the session")
    console.print(perm)
    console.print()

    console.print(Text("  Tips", style="bold kaicode.assistant"))
    console.print(Text("  ·  @path        include a specific file as context  (e.g. @kaicode/app.py)", style="kaicode.muted"))
    console.print(Text("  ·  !command     run a shell command inline  (e.g. !git status)",             style="kaicode.muted"))
    console.print(Text("  ·  /undo        safely revert the agent's last file change",                 style="kaicode.muted"))
    console.print(Text("  ·  KAICODE.md   standing instructions, auto-loaded every session",           style="kaicode.muted"))
    console.print(Text("  ·  Read-only tools run without asking; writes/exec ask first",               style="kaicode.muted"))
    console.print()
