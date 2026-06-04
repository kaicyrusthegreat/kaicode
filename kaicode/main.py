"""KaiCode entry point — interactive REPL and CLI."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import Completer, Completion
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from kaicode.config import KaiConfig, create_default_config
from kaicode.ui.display import (
    console,
    print_splash,
    print_header,
    print_error,
    print_info,
    print_success,
    print_help,
    print_user_message,
    _MODEL_LABELS,
)
from kaicode.ui.theme import KAICODE_THEME
from kaicode.session import Session, SESSIONS_DIR


HISTORY_FILE = Path.home() / ".kaicode" / "history"

PT_STYLE = PTStyle.from_dict({
    "prompt":         "fg:#50fa7b bold",
    "":               "fg:#e8f5e9",
    "bottom-toolbar": "noreverse",
    "completion-menu":                "bg:#1e1e2e fg:#cdd6f4",
    "completion-menu.completion":     "bg:#1e1e2e fg:#cdd6f4",
    "completion-menu.completion.current": "bg:#45475a fg:#50fa7b bold",
    "completion-menu.meta":           "fg:#6c7086 italic",
    "completion-menu.meta.current":   "fg:#a6e3a1 italic",
})


# ── Slash command completer ───────────────────────────────────────────────────

_SLASH_COMMANDS = [
    ("/model",    "Switch model — shows picker if no name given"),
    ("/provider", "Switch provider (ollama/openai/openai/groq)"),
    ("/save",     "Save current conversation"),
    ("/load",     "Load a saved conversation"),
    ("/sessions", "List all saved sessions"),
    ("/diff",     "Show the last applied diff"),
    ("/context",  "Show auto-detected context files"),
    ("/memory",   "Show project memory (/memory clear to reset)"),
    ("/clear",    "Clear conversation history"),
    ("/status",   "Show tokens, model, and provider"),
    ("/help",     "Show all commands"),
    ("/quit",     "Exit KaiCode"),
]


class SlashCompleter(Completer):
    """Show slash commands when the user types '/'."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        if not text.startswith("/"):
            return
        for cmd, desc in _SLASH_COMMANDS:
            if cmd.startswith(text):
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=desc,
                )


def _make_toolbar(app):
    """Two-line footer pinned to the bottom: status row + hints row.

    Kept to plain text lines (no separators / backgrounds / manual cursor
    tricks) so prompt_toolkit manages the geometry cleanly without ghosting.
    """
    def _toolbar():
        tok  = f"~{app.tokens_used:,} tok" if app.tokens_used else "0 tok"
        msgs = len(app.session.messages)
        return FormattedText([
            # Row 1 — live status
            ("fg:#555555",      "  ◈  "),
            ("fg:#00838f",      f"{app.provider_name}"),
            ("fg:#444444",      " / "),
            ("fg:#e65100 bold", f"{app.model}"),
            ("fg:#555555",      f"  ·  {tok}  ·  {msgs} msgs  ·  by Kai Cyrus"),
            ("",                "\n"),
            # Row 2 — hints
            ("fg:#666666",      "  ESC"),
            ("fg:#555555",      " cancel  ·  "),
            ("fg:#666666",      "/"),
            ("fg:#555555",      " commands  ·  "),
            ("fg:#666666",      "Ctrl+C"),
            ("fg:#555555",      " quit"),
        ])
    return _toolbar


async def run_interactive(app) -> None:
    """Run the interactive REPL loop."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    ps = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=SlashCompleter(),
        style=PT_STYLE,
        mouse_support=False,
        bottom_toolbar=_make_toolbar(app),
    )

    print_splash()
    app.print_header()
    print_info(
        f"Provider: {app.provider_name}  ·  Model: {app.model}  ·  "
        f"Project: {app.project_info.description}  ·  /help for commands, /quit to exit"
    )
    console.print()

    while True:
        try:
            prompt_fmt = FormattedText([("fg:#50fa7b bold", "›  ")])
            user_input = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ps.prompt(prompt_fmt, style=PT_STYLE),
            )
            # Erase the echoed prompt line so the message shows only in its bubble
            sys.stdout.write("\x1b[1A\x1b[2K\r")
            sys.stdout.flush()
        except (KeyboardInterrupt, EOFError):
            console.print()
            print_info("Goodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            await handle_command(user_input, app)
            continue

        print_user_message(user_input)
        await app.chat(user_input)


async def handle_command(cmd: str, app) -> None:
    """Handle slash commands."""
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if command in ("/quit", "/q", "/exit"):
        console.print()
        print_info("Goodbye!")
        sys.exit(0)

    elif command == "/help":
        print_help()

    elif command == "/clear":
        app.clear_history()

    elif command == "/model":
        if args:
            await app.switch_model(args)
        else:
            models = await app.list_models()
            if not models:
                print_error("No models available. Is your provider configured?")
                return
            await _pick_model(models, app)

    elif command == "/provider":
        if args:
            parts2 = args.split()
            provider = parts2[0]
            model = parts2[1] if len(parts2) > 1 else None
            try:
                await app.switch_provider(provider, model)
            except ValueError as e:
                print_error(str(e))
        else:
            print_info("Available providers: ollama, openai, openai, groq, openai_compat, cyrusai")
            print_info(f"Current: {app.provider_name}")
            print_info("Use: /provider <name> [model]")

    elif command == "/diff":
        if app.last_diff:
            from kaicode.ui.display import _print_diff
            _print_diff(app.last_diff)
        else:
            print_info("No diff available.")

    elif command in ("/apply", "/reject"):
        print_info("Changes are applied directly as KaiCode makes them.")
        print_info("To undo: use git to revert, or ask KaiCode to revert the change.")

    elif command == "/save":
        app.save_session(args or None)

    elif command == "/load":
        if args:
            app.load_session(args)
        else:
            print_info("Use: /load <session-name>")

    elif command == "/sessions":
        sessions = Session.list_sessions()
        if not sessions:
            print_info("No saved sessions.")
        else:
            t = Table(
                title=" Saved Sessions ",
                box=box.ROUNDED,
                border_style="kaicode.separator",
                title_style="bold kaicode.logo",
                header_style="kaicode.muted",
                padding=(0, 1),
            )
            t.add_column("Name", style="bold kaicode.assistant")
            t.add_column("Provider", style="kaicode.info")
            t.add_column("Model", style="kaicode.model")
            t.add_column("Messages", justify="right", style="dim")
            t.add_column("Updated", style="dim")
            for s in sessions:
                ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(s["updated_at"]))
                t.add_row(s["name"], s["provider"], s["model"], str(s["messages"]), ts)
            console.print()
            console.print(t)
            console.print()

    elif command == "/status":
        tok = f"~{app.tokens_used:,}" if app.tokens_used else "0"
        console.print()
        print_info(f"Provider: {app.provider_name}  ·  Model: {app.model}  ·  {tok} tokens")
        print_info(f"Project: {app.project_info.description}")
        print_info(f"Messages in history: {len(app.session.messages)}")
        console.print()

    elif command == "/memory":
        from kaicode.tools.memory_tools import read_memory, clear_memory
        if args == "clear":
            clear_memory(app.cwd)
            print_success("Project memory cleared.")
        else:
            mem = read_memory(app.cwd)
            if mem.strip():
                from rich.markdown import Markdown
                console.print()
                console.print(Markdown(mem))
                console.print()
            else:
                print_info("No memory saved for this project yet.")
                print_info("The model will save notes automatically using update_memory.")

    elif command == "/context":
        if app.project_info.context_files:
            print_info("Auto-detected context files:")
            for f in app.project_info.context_files:
                console.print(f"  [kaicode.info]{f}[/]")
        else:
            print_info("No context files auto-detected.")

    else:
        print_error(f"Unknown command: {command}  —  type /help for available commands.")


# Preferred order based on actual KaiCode test results (best first)
_MODEL_RANK = [
    "qwen3:8b",           # 🥇 Best overall — reasoning + tool-calling + verification
    "qwen2.5-coder:7b",   # 🥈 Best for code — specialized, reliable tools
    "qwen3:4b",           # 🥉 Best bang-for-buck — tiny but full tool support
    "granite4:3b",        # Smallest model that works flawlessly
    "gemma4:latest",      # Reliable, clean output
    "gemma3:4b",          # Fast, compact Google model
    "llama3.1:8b",        # Solid workhorse
    "llama3.2:latest",    # Good for chat, weak on tools
    "phi4:latest",        # Great reasoning, no native tools
    "gpt-oss:20b",        # Large, slow, no native tools
    "devstral:latest",    # Heavy — agentic coding
    "qwen3-coder:latest", # Heavy — advanced coding
    "deepseek-r1:8b",     # Heavy — step-by-step reasoning
]


def _rank_key(model_name: str) -> int:
    """Return sort key: ranked models get their index, unknown ones go to end."""
    try:
        return _MODEL_RANK.index(model_name)
    except ValueError:
        return len(_MODEL_RANK)


async def _pick_model(models: list[str], app) -> None:
    """Show a numbered model list with descriptions and let the user pick."""
    # Sort models by test ranking (best first), unknowns at end alphabetically
    models = sorted(models, key=lambda m: (_rank_key(m), m))

    lines = Text()
    for i, m in enumerate(models, 1):
        active     = m == app.model
        num_style  = "bold kaicode.success" if active else "bold kaicode.assistant"
        name_style = "bold kaicode.success" if active else "bold default"
        desc       = _MODEL_LABELS.get(m, "")
        tick       = "  ✓  active" if active else ""

        # Model number + name
        lines.append(f"\n  {i:>2}.  ", style=num_style)
        lines.append(f"{m}", style=name_style)
        if tick:
            lines.append(tick, style="bold kaicode.success")
        lines.append("\n")

        # Description indented below
        if desc:
            lines.append(f"       {desc}\n", style="kaicode.muted")

    console.print()
    console.print(Panel(
        lines,
        title=f"[bold kaicode.logo] Select a model — {app.provider_name} [/]",
        border_style="kaicode.separator",
        padding=(0, 1),
    ))
    console.print(Text("  Enter number or model name (Enter to cancel): ", style="bold kaicode.assistant"), end="")

    try:
        answer = await asyncio.get_event_loop().run_in_executor(None, input)
    except (KeyboardInterrupt, EOFError):
        console.print()
        return

    answer = answer.strip()
    if not answer:
        return

    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(models):
            await app.switch_model(models[idx])
        else:
            print_error(f"No model #{answer}. Pick 1–{len(models)}.")
    else:
        await app.switch_model(answer)


@click.command()
@click.option("--provider", "-p", default=None, help="AI provider (ollama/openai/openai/groq)")
@click.option("--model", "-m", default=None, help="Model name")
@click.option("--session", "-s", default=None, help="Load a saved session")
@click.option("--config", "-c", "config_path", default=None, help="Path to config file")
@click.version_option(version="2.0.2", prog_name="kaicode")
@click.argument("prompt", nargs=-1)
def main(provider, model, session, config_path, prompt):
    """KaiCode — Terminal AI coding assistant.\n\nSupports Ollama, OpenAI, OpenAI, Groq, and any OpenAI-compatible API."""
    create_default_config()

    config = KaiConfig.load()

    from kaicode.app import KaiApp

    try:
        app = KaiApp(config, provider_name=provider, model=model)
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    if session:
        app.load_session(session)

    async def _run():
        if prompt:
            user_input = " ".join(prompt)
            app.print_header()
            print_user_message(user_input)
            await app.chat(user_input)
        else:
            await run_interactive(app)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print()
        print_info("Interrupted.")


if __name__ == "__main__":
    main()
