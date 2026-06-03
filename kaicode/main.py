"""KaiCode entry point — interactive REPL and CLI."""

from __future__ import annotations

import asyncio
import shutil
import sys
import time
from pathlib import Path

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.styles import Style as PTStyle
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
    print_status,
    print_user_message,
    _MODEL_LABELS,
)
from kaicode.ui.theme import KAICODE_THEME
from kaicode.session import Session, SESSIONS_DIR


HISTORY_FILE = Path.home() / ".kaicode" / "history"

PT_STYLE = PTStyle.from_dict({
    "prompt":         "bold",
    "":               "default",
    "bottom-toolbar": "noreverse",
})


def _make_toolbar(app):
    """Two-line bottom toolbar: separator then info row with left/right content."""
    def _toolbar():
        width = shutil.get_terminal_size((80, 20)).columns
        sep   = "─" * width

        left  = " ⏵⏵ accept edits on  (shift+tab to cycle)  ·  ← for agents"
        tok   = f"~{app.tokens_used:,} tok" if app.tokens_used else "0 tok"
        right = f"{app.provider_name} / {app.model}  ·  {tok}  "
        gap   = " " * max(1, width - len(left) - len(right))

        return FormattedText([
            ("fg:#3a3a3a",  sep),
            ("",            "\n"),
            ("fg:#2196f3 bold", " ⏵⏵ accept edits on"),
            ("fg:#666666",  "  (shift+tab to cycle)  ·  ← for agents"),
            ("fg:#444444",  gap),
            ("fg:#666666",  right),
        ])
    return _toolbar


async def run_interactive(app) -> None:
    """Run the interactive REPL loop."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    ps = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        style=PT_STYLE,
        mouse_support=False,
        bottom_toolbar=_make_toolbar(app),
    )

    print_splash()
    app.print_header()
    print_info(f"Provider: {app.provider_name}  ·  Model: {app.model}")
    print_info(f"Project: {app.project_info.description}")
    print_info("Type /help for commands, /quit to exit.")
    console.print()

    while True:
        try:
            console.rule(style="dim #3a3a3a")
            user_input = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ps.prompt("› ", style=PT_STYLE),
            )
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
        print_status(app.tokens_used, app.model, app.provider_name)


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
            print_info("Available providers: ollama, openai, openai, groq, openai_compat")
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
        console.print()
        print_status(app.tokens_used, app.model, app.provider_name, "ready")
        print_info(f"Project: {app.project_info.description}")
        print_info(f"Messages in history: {len(app.session.messages)}")
        console.print()

    elif command == "/context":
        if app.project_info.context_files:
            print_info("Auto-detected context files:")
            for f in app.project_info.context_files:
                console.print(f"  [kaicode.info]{f}[/]")
        else:
            print_info("No context files auto-detected.")

    else:
        print_error(f"Unknown command: {command}  —  type /help for available commands.")


async def _pick_model(models: list[str], app) -> None:
    """Show a numbered model list and let the user pick by number or name."""
    lines = Text()
    for i, m in enumerate(models, 1):
        active = m == app.model
        num_style  = "bold kaicode.success" if active else "bold kaicode.assistant"
        name_style = "bold default" if active else "default"
        label = _MODEL_LABELS.get(m, "")
        tick = " ✓" if active else ""

        lines.append(f"  {i:>2}. ", style=num_style)
        lines.append(f"{m}{tick}", style=name_style)
        if label:
            lines.append(f"  {label}", style="kaicode.muted")
        lines.append("\n")

    console.print()
    console.print(Panel(
        lines,
        title=f"[bold kaicode.logo] Models — {app.provider_name} [/]",
        border_style="kaicode.separator",
        padding=(0, 1),
    ))
    console.print(Text("  Pick a number or model name (Enter to cancel): ", style="bold kaicode.assistant"), end="")

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
@click.version_option(version="1.0.1", prog_name="kaicode")
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
