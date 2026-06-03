"""Core KaiCode application — the agentic loop."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from kaicode.config import KaiConfig
from kaicode.providers import get_provider, BaseProvider
from kaicode.providers.base import Message, StreamChunk
from kaicode.session import Session
from kaicode.tools.registry import ToolRegistry, TOOL_DEFINITIONS
from kaicode.project_detector import detect_project, build_system_prompt
from kaicode.ui.display import (
    console,
    print_header,
    print_tool_call,
    print_tool_result,
    print_error,
    print_info,
    print_success,
    print_kai_message,
    print_status,
    print_help,
)


MAX_TOOL_ITERATIONS = 10


class _StreamStatus:
    """Live display shown while the AI is generating a response."""

    _PHASES = ["Thinking", "Reasoning", "Deciphering", "Processing"]

    def __init__(self, label: str = "") -> None:
        self._start = time.monotonic()
        self._label = label

    def _elapsed(self) -> int:
        return int(time.monotonic() - self._start)

    def __rich__(self) -> Text:
        elapsed = self._elapsed()
        if self._label:
            phase = self._label
        else:
            phase = self._PHASES[min(elapsed // 6, len(self._PHASES) - 1)]

        t = Text()
        t.append("  ✽ ", style="kaicode.assistant")
        t.append(f"{phase}… ", style="kaicode.info")
        t.append(f"({elapsed}s)", style="kaicode.muted")
        return t

# Tools that are read-only and safe to run without asking
_AUTO_APPROVE_TOOLS = {
    "read_file",
    "list_files",
    "search_files",
    "git_status",
    "git_diff",
}

# Human-readable descriptions for the permission prompt
_TOOL_ACTION_LABELS = {
    "edit_file":        "Edit file",
    "create_file":      "Create file",
    "create_directory": "Create directory",
    "run_command":      "Run command",
    "git_commit":       "Git commit",
}

def _format_permission_detail(tool_name: str, args: dict) -> str:
    """One-line summary of what the tool will do."""
    if tool_name == "edit_file":
        return args.get("path", "?")
    if tool_name == "create_file":
        return args.get("path", "?")
    if tool_name == "create_directory":
        return args.get("path", "?")
    if tool_name == "run_command":
        return f"$ {args.get('command', '?')}"
    if tool_name == "git_commit":
        return f'git commit -m "{args.get("message", "?")}"'
    return str(args)[:80]


# Keywords that suggest the user wants file/code operations
_TOOL_TRIGGERS = {
    "file", "edit", "create", "read", "open", "write", "delete", "remove",
    "search", "find", "grep", "look", "run", "execute", "command", "test",
    "install", "build", "compile", "commit", "git", "diff", "change",
    "fix", "refactor", "add", "implement", "update", "show", "list",
    "directory", "folder", "mkdir", "rename", "move", "copy",
    "function", "class", "import", "module", "code",
    "error", "bug", "debug", "check", "review",
}


def _needs_tools(message: str) -> bool:
    """Heuristic: only offer tools if the message looks like a code/file task."""
    lower = message.lower()
    words = set(lower.split())
    # Direct mentions of files (has extension or slash)
    if any(("." in w and len(w) > 3) or "/" in w for w in words):
        return True
    return bool(words & _TOOL_TRIGGERS)


class KaiApp:
    def __init__(self, config: KaiConfig, provider_name: str | None = None, model: str | None = None) -> None:
        self.config = config
        self.provider_name = provider_name or config.default_provider
        self.provider: BaseProvider = get_provider(self.provider_name, config)
        self.model = model or config.get_provider(self.provider_name).default_model or self._default_model()
        self.cwd = os.getcwd()
        self.session = Session(
            name="",
            provider=self.provider_name,
            model=self.model,
            cwd=self.cwd,
        )
        self.project_info = detect_project(self.cwd)
        self.tool_registry = ToolRegistry(cwd=self.cwd)
        self.last_diff: str = ""
        self.last_suggestion: str = ""
        self._tokens_used: int = 0
        self._always_allowed: set[str] = set()  # tools approved with "a" this session
        self._tools_disabled: bool = False      # True when model doesn't support tools

    def _default_model(self) -> str:
        defaults = {
            "ollama": "llama3.2",
            "openai": "model-sonnet-4-6",
            "openai": "gpt-4o",
            "groq": "llama-3.1-70b-versatile",
            "openai_compat": "default",
        }
        return defaults.get(self.provider_name, "default")

    def print_header(self) -> None:
        print_header(self.model, self.provider_name, self.cwd)

    def _system_prompt(self) -> str:
        base = build_system_prompt(self.project_info, self.config.system_prompt)
        return base

    async def chat(self, user_input: str) -> None:
        """Process one user turn through the agentic loop."""
        self.session.messages.append(Message(role="user", content=user_input))

        for iteration in range(MAX_TOOL_ITERATIONS):
            assistant_content = ""
            pending_tool_call: dict | None = None
            usage: dict | None = None
            live_stopped = False

            label = "Working" if iteration > 0 else ""
            live = Live(
                _StreamStatus(label),
                console=console,
                transient=True,
                refresh_per_second=10,
            )
            live.start()

            if self._tools_disabled and iteration == 0 and _needs_tools(user_input):
                live.stop()
                live_stopped = True
                console.print()
                console.print(Panel(
                    Text.assemble(
                        ("  ⚠  ", "kaicode.warning"),
                        (f"'{self.model}' doesn't support tools — KaiCode can't take actions.\n\n", "default"),
                        ("  Switch to a tool-capable model with ", "kaicode.muted"),
                        ("/model", "bold kaicode.assistant"),
                        (" and try again.\n", "kaicode.muted"),
                        ("  Ollama models with tool support: ", "kaicode.muted"),
                        ("llama3.1  llama3.2  qwen2.5-coder  mistral-nemo", "kaicode.info"),
                    ),
                    border_style="kaicode.warning",
                    padding=(0, 1),
                ))
                return

            active_tools = (
                None if self._tools_disabled
                else TOOL_DEFINITIONS if _needs_tools(user_input)
                else None
            )

            try:
                stream = self.provider.stream_chat(
                    messages=self.session.messages,
                    model=self.model,
                    system=self._system_prompt(),
                    tools=active_tools,
                )
                # Collect the full response silently — render it all at once after
                async for chunk in stream:
                    if chunk.content:
                        assistant_content += chunk.content
                    if chunk.tool_call:
                        pending_tool_call = chunk.tool_call
                    if chunk.usage:
                        usage = chunk.usage
                    if chunk.done:
                        break
            except Exception as e:
                if not live_stopped:
                    live.stop()
                    live_stopped = True
                err = str(e)
                if "does not support tools" in err.lower():
                    self._tools_disabled = True
                    print_info(f"'{self.model}' doesn't support tools — switching to text-only mode.")
                    self.session.messages.pop()
                    await self.chat(user_input)
                    return
                # Only auto-switch on a true HTTP 404 (model not installed in Ollama)
                if "ollama error 404" in err.lower() and self.provider_name == "ollama":
                    available = await self.provider.list_models()
                    if available:
                        self.model = available[0]
                        self.session.model = self.model
                        print_error(f"Model '{self.model}' not found in Ollama. Auto-switching to: {self.model}")
                        self.print_header()
                        self.session.messages.pop()
                        await self.chat(user_input)
                    else:
                        print_error("No Ollama models installed. Run: ollama pull llama3.2")
                    return
                print_error(f"Provider error: {e}")
                return
            finally:
                if not live_stopped:
                    live.stop()

            if usage:
                tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                self._tokens_used += tokens
                self.session.add_tokens(tokens)

            # Render the full response at once now that we have it all
            if assistant_content:
                print_kai_message(assistant_content)
                self.session.messages.append(
                    Message(role="assistant", content=assistant_content)
                )

            if not pending_tool_call:
                break

            # Handle tool call
            console.print()
            tool_name = pending_tool_call.get("name", "")
            tool_args = pending_tool_call.get("input", {})
            tool_id   = pending_tool_call.get("id", "")

            approved = await self._request_permission(
                tool_name, tool_args, reason=assistant_content.strip()
            )
            if not approved:
                result = json.dumps({"error": "User denied this action."})
            else:
                print_tool_call(tool_name, tool_args)
                result = self.tool_registry.call(tool_name, tool_args)
                print_tool_result(tool_name, result)

            if tool_name == "edit_file":
                try:
                    rdata = json.loads(result)
                    if "diff" in rdata:
                        self.last_diff = rdata["diff"]
                except json.JSONDecodeError:
                    pass

            self.session.messages.append(Message(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": tool_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
                }],
            ))
            self.session.messages.append(Message(
                role="tool",
                content=result,
                tool_results=[{"tool_use_id": tool_id, "content": result}],
            ))

    async def _request_permission(
        self, tool_name: str, tool_args: dict, reason: str = ""
    ) -> bool:
        """Ask the user to approve a tool call. Returns True if approved."""
        if tool_name in _AUTO_APPROVE_TOOLS:
            return True
        if tool_name in self._always_allowed:
            return True

        label = _TOOL_ACTION_LABELS.get(tool_name, tool_name)
        detail = _format_permission_detail(tool_name, tool_args)

        # Build the permission panel content
        body = Text()

        # What it wants to do
        body.append("  What:  ", style="bold cyan")
        body.append(f"{label}\n", style="bold white")

        # The specific action detail
        body.append("  Action: ", style="bold cyan")
        body.append(f"{detail}\n", style="yellow")

        # Why (from the model's reasoning text before the tool call)
        if reason:
            # Trim to first 2 sentences to keep it concise
            sentences = reason.replace("\n", " ").split(". ")
            short_reason = ". ".join(sentences[:2]).strip()
            if len(short_reason) > 200:
                short_reason = short_reason[:200] + "…"
            body.append("\n  Why:   ", style="bold cyan")
            body.append(f"{short_reason}\n", style="dim white")

        # Numbered options
        body.append("\n")
        body.append("  1. ", style="bold green")
        body.append("Yes, do it\n", style="white")
        body.append("  2. ", style="bold red")
        body.append("No, skip this action\n", style="white")
        body.append("  3. ", style="bold cyan")
        body.append(f"Yes, and always allow '{tool_name}' this session\n", style="white")
        body.append("  4. ", style="bold magenta")
        body.append("Yes, and allow ALL tools this session\n", style="white")

        console.print()
        console.print(Panel(
            body,
            title="[bold kaicode.warning] Permission required [/]",
            border_style="kaicode.warning",
            padding=(0, 1),
        ))
        console.print(Text("  Choose [1/2/3/4]: ", style="bold kaicode.assistant"), end="")

        try:
            answer = await asyncio.get_event_loop().run_in_executor(None, input)
        except (KeyboardInterrupt, EOFError):
            console.print()
            return False

        answer = answer.strip().lower()

        if answer in ("1", "y", "yes", ""):
            return True
        elif answer in ("3", "a", "always"):
            self._always_allowed.add(tool_name)
            print_info(f"Always allowing '{tool_name}' this session.")
            return True
        elif answer in ("4", "!"):
            self._always_allowed.update(_TOOL_ACTION_LABELS.keys())
            print_info("Always allowing all tools this session.")
            return True
        else:
            # 2, n, no, or anything else
            return False

    async def list_models(self) -> list[str]:
        return await self.provider.list_models()

    async def switch_model(self, model: str) -> None:
        self.model = model
        self.session.model = model
        self._tools_disabled = False
        print_success(f"Switched to model: {model}")
        self.print_header()

    async def switch_provider(self, provider_name: str, model: str | None = None) -> None:
        self.provider_name = provider_name
        self.provider = get_provider(provider_name, self.config)
        self.model = model or self.config.get_provider(provider_name).default_model or self._default_model()
        self.session.provider = provider_name
        self.session.model = self.model
        self._tools_disabled = False
        print_success(f"Switched to provider: {provider_name} / {self.model}")
        self.print_header()

    def clear_history(self) -> None:
        self.session.messages.clear()
        self._tokens_used = 0
        self.last_diff = ""
        print_info("Conversation cleared.")

    def save_session(self, name: str | None = None) -> None:
        path = self.session.save(name)
        print_success(f"Session saved: {path}")

    def load_session(self, name: str) -> None:
        try:
            self.session = Session.load(name)
            self.provider_name = self.session.provider
            self.provider = get_provider(self.provider_name, self.config)
            self.model = self.session.model
            self._tokens_used = self.session.total_tokens
            print_success(f"Loaded session '{name}' ({len(self.session.messages)} messages)")
            self.print_header()
        except FileNotFoundError:
            print_error(f"Session not found: {name}")

    @property
    def tokens_used(self) -> int:
        return self._tokens_used


