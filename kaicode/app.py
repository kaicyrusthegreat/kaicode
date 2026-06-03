"""Core KaiCode application — the agentic loop."""

from __future__ import annotations

import asyncio
import json
import os
import re
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
    print_plan,
)


MAX_TOOL_ITERATIONS = 10
MAX_HISTORY_MESSAGES = 50   # trim older messages beyond this

# ── Tool selection ────────────────────────────────────────────────────────────

_CORE_TOOL_NAMES = {
    "read_file", "edit_file", "create_file", "create_directory",
    "list_files", "search_files", "run_command",
}

def _select_tools(message: str) -> list[dict]:
    """Return the relevant tool subset. Core tools always; extras only when hinted."""
    lower = message.lower()
    names = set(_CORE_TOOL_NAMES)
    if any(w in lower for w in ("git", "commit", "push", "branch", "diff", "staged", "merge")):
        names |= {"git_status", "git_commit", "git_diff"}
    if any(w in lower for w in ("test", "spec", "pytest", "unittest", "jest", "flutter test")):
        names.add("run_tests")
    if any(w in lower for w in ("memory", "remember", "note", "save for later")):
        names.add("update_memory")
    if any(w in lower for w in ("symbol", "function", "class", "def ", "struct", "interface", "ast")):
        names.add("grep_ast")
    if any(w in lower for w in ("structure", "overview", "architecture", "codebase",
                                "the project", "this project", "the repo", "understand",
                                "explain the", "how does this", "where is")):
        names.add("repo_map")
        names.add("grep_ast")
    if any(w in lower for w in ("http", "url", "web", "doc", "fetch", "documentation", "api reference")):
        names.add("web_fetch")
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in names]


# ── Intent heuristics ─────────────────────────────────────────────────────────

_CHAT_RE = re.compile(
    r'^(?:'
    r'hi|hello|hey|yo|sup|howdy|'
    r'thanks|thank you|ty|thx|'
    r'ok|okay|sure|yep|yeah|nope|nah|'
    r'bye|goodbye|'
    r'good|great|nice|cool|awesome|perfect|got it|sounds good|makes sense|'
    r'what is\b|what are\b|what\'s\b|'
    r'who is\b|who are\b|'
    r'why is\b|why does\b|why do\b|'
    r'how does\b|how do\b|how is\b|how are\b|'
    r'explain\b|tell me\b|can you explain\b|'
    r'what do you\b|what\'s the difference\b|'
    r'lol|haha|hehe'
    r')',
    re.I,
)

_HAS_TASK = re.compile(
    r'(?:^|[\s"])/[\w./]+'
    r'|\b[\w./\-]+\.(?:py|js|ts|dart|go|rs|rb|java|kt|tsx|jsx|vue|'
    r'yaml|yml|json|toml|md|sh|css|html|swift|cs|cpp|c|h)\b'
    r'|\b(?:'
    r'file|folder|dir(?:ectory)?|create|make|edit|update|fix|refactor|'
    r'read|write|delete|remove|rename|move|copy|'
    r'run|execute|install|build|compile|test|commit|push|'
    r'search|find|grep|implement|add|generate|scaffold'
    r')\b',
    re.I,
)

def _sanitize_json_block(block: str) -> str:
    """Escape raw control chars that appear inside JSON string values, so
    json.loads accepts the not-quite-valid JSON that local models emit
    (e.g. real newlines inside a 'content' field holding source code)."""
    out: list[str] = []
    in_str = False
    esc = False
    for c in block:
        if in_str:
            if esc:
                out.append(c)
                esc = False
            elif c == "\\":
                out.append(c)
                esc = True
            elif c == '"':
                out.append(c)
                in_str = False
            elif c == "\n":
                out.append("\\n")
            elif c == "\r":
                out.append("\\r")
            elif c == "\t":
                out.append("\\t")
            else:
                out.append(c)
        else:
            out.append(c)
            if c == '"':
                in_str = True
    return "".join(out)


def _extract_text_tool_calls(content: str, valid_names: set[str]) -> tuple[str, list[dict]]:
    """Fallback: parse tool calls that a model emitted as JSON text instead of
    using the native tool-calling channel (very common with local models).

    Returns (cleaned_content, tool_calls). Each tool call is {id, name, input}.
    """
    if not content or "{" not in content:
        return content, []

    calls: list[dict] = []
    spans: list[tuple[int, int]] = []

    i = 0
    n = len(content)
    while i < n:
        if content[i] != "{":
            i += 1
            continue
        # Scan for a balanced {...} block (string-aware)
        depth = 0
        j = i
        in_str = False
        esc = False
        while j < n:
            c = content[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
            j += 1

        if depth != 0:
            break  # unbalanced — stop scanning

        block = content[i:j + 1]
        try:
            import json as _json
            obj = _json.loads(_sanitize_json_block(block))
        except (ValueError, TypeError):
            i += 1
            continue

        if isinstance(obj, dict):
            name = obj.get("name") or obj.get("tool") or obj.get("function")
            args = obj.get("arguments")
            if args is None:
                args = obj.get("parameters")
            if args is None:
                args = obj.get("input")
            if isinstance(name, str) and name in valid_names:
                if isinstance(args, str):
                    try:
                        import json as _json2
                        args = _json2.loads(args)
                    except (ValueError, TypeError):
                        args = {}
                if not isinstance(args, dict):
                    args = {}
                calls.append({
                    "id": f"text_{len(calls)}_{abs(hash(name)) % 100000}",
                    "name": name,
                    "input": args,
                })
                spans.append((i, j + 1))
        i = j + 1

    # Strip the parsed JSON blocks from the visible content
    if spans:
        cleaned_parts = []
        last = 0
        for s, e in spans:
            cleaned_parts.append(content[last:s])
            last = e
        cleaned_parts.append(content[last:])
        cleaned = "".join(cleaned_parts)
        # Tidy leftover fences/whitespace
        cleaned = re.sub(r'```(?:json|tool_code)?\s*```', '', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        return cleaned, calls

    return content, []


def _needs_tools(message: str) -> bool:
    msg = message.strip()
    if _HAS_TASK.search(msg):
        return True
    if _CHAT_RE.match(msg) and len(msg) < 120:
        return False
    if len(msg) < 30:
        return False
    return True

def _is_real_plan(text: str) -> bool:
    """True only when the model wrote a genuine numbered list (2+ steps)."""
    items = re.findall(r'(?:^|\n)\s*[1-9]\d*[.)]\s+\w', text)
    return len(items) >= 2

# Substrings that indicate a retryable, transient provider failure
_TRANSIENT_MARKERS = (
    "429", "500", "502", "503", "504",
    "timeout", "timed out", "connect", "overloaded",
    "temporarily", "rate limit", "read error", "remote protocol",
)

def _is_transient(err: str) -> bool:
    low = err.lower()
    return any(m in low for m in _TRANSIENT_MARKERS)

MAX_RETRIES = 2


# ── Permission helpers ────────────────────────────────────────────────────────

_AUTO_APPROVE_TOOLS = {
    "read_file", "list_files", "search_files",
    "git_status", "git_diff",
    "grep_ast",      # read-only symbol search
    "web_fetch",     # read-only URL fetch
    "update_memory", # user's own persistent notes
    "repo_map",      # read-only codebase index
}

_TOOL_ACTION_LABELS = {
    "edit_file":        "Edit file",
    "create_file":      "Create file",
    "create_directory": "Create directory",
    "run_command":      "Run command",
    "git_commit":       "Git commit",
    "run_tests":        "Run test suite",
}

def _format_permission_detail(tool_name: str, args: dict) -> str:
    if tool_name in ("edit_file", "create_file", "create_directory"):
        return args.get("path", "?")
    if tool_name == "run_command":
        return f"$ {args.get('command', '?')}"
    if tool_name == "git_commit":
        return f'git commit -m "{args.get("message", "?")}"'
    if tool_name == "run_tests":
        return args.get("command", "auto-detect")
    return str(args)[:80]


# ── Streaming status display ──────────────────────────────────────────────────

class _StreamStatus:
    _PHASES = ["Thinking", "Reasoning", "Deciphering", "Processing"]

    def __init__(self, label: str = "") -> None:
        self._start = time.monotonic()
        self._label = label

    def _elapsed(self) -> int:
        return int(time.monotonic() - self._start)

    def __rich__(self) -> Text:
        elapsed = self._elapsed()
        phase = self._label or self._PHASES[min(elapsed // 6, len(self._PHASES) - 1)]
        t = Text()
        t.append("  ✽ ", style="kaicode.assistant")
        t.append(f"{phase}… ", style="kaicode.info")
        t.append(f"({elapsed}s)", style="kaicode.muted")
        return t


# ── Main application ──────────────────────────────────────────────────────────

class KaiApp:
    def __init__(self, config: KaiConfig, provider_name: str | None = None, model: str | None = None) -> None:
        self.config = config
        self.provider_name = provider_name or config.default_provider
        self.provider: BaseProvider = get_provider(self.provider_name, config)
        self.model = model or config.get_provider(self.provider_name).default_model or self._default_model()
        self.cwd = os.getcwd()
        self.session = Session(
            name="", provider=self.provider_name, model=self.model, cwd=self.cwd,
        )
        self.project_info = detect_project(self.cwd)
        self.tool_registry = ToolRegistry(cwd=self.cwd)
        self.last_diff: str = ""
        self._tokens_used: int = 0
        self._always_allowed: set[str] = set()
        self._tools_disabled: bool = False

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
        return build_system_prompt(self.project_info, self.config.system_prompt)

    def _trim_messages(self, messages: list[Message]) -> list[Message]:
        """Keep history within MAX_HISTORY_MESSAGES, never split mid-tool-call."""
        if len(messages) <= MAX_HISTORY_MESSAGES:
            return messages
        trimmed = messages[-MAX_HISTORY_MESSAGES:]
        # Don't start on a tool result — shift until we find user/assistant
        while trimmed and trimmed[0].role == "tool":
            trimmed = trimmed[1:]
        return trimmed

    def _find_relevant_files(self, user_input: str) -> list[tuple[str, str]]:
        """Auto-detect files relevant to the user's message."""
        MAX_FILES = 3
        MAX_CHARS = 2500
        found: dict[str, str] = {}

        backtick  = re.findall(r'`([^`]+)`', user_input)
        file_refs = re.findall(
            r'\b([\w./\-]+\.(?:py|js|ts|dart|go|rs|rb|java|kt|swift|tsx|jsx|vue|css|yaml|yml|json|toml|md))\b',
            user_input
        )
        sym_refs = re.findall(
            r'(?:in|the|function|class|method|def|fix|update|edit|read|check|look at)\s+["\']?([\w_]{3,})["\']?',
            user_input, re.I
        )

        def _read(rel_path: str) -> str | None:
            p = Path(self.cwd) / rel_path
            if p.is_file() and p.stat().st_size < 200_000:
                return p.read_text("utf-8", errors="replace")[:MAX_CHARS]
            return None

        def _search_and_read(pattern: str, use_regex: bool = False) -> None:
            if len(found) >= MAX_FILES:
                return
            try:
                data = json.loads(self.tool_registry.call("search_files", {
                    "pattern": pattern, "use_regex": use_regex, "max_results": 2
                }))
                for r in data.get("results", []):
                    fp = r["file"]
                    if fp not in found:
                        content = _read(fp)
                        if content:
                            found[fp] = content
                            break
            except Exception:
                pass

        for candidate in (backtick + file_refs):
            if len(found) >= MAX_FILES:
                break
            content = _read(candidate)
            if content:
                found[candidate] = content
            else:
                _search_and_read(re.escape(candidate))

        for sym in sym_refs:
            if len(found) >= MAX_FILES:
                break
            _search_and_read(rf"\b{re.escape(sym)}\b", use_regex=True)

        return list(found.items())

    async def chat(self, user_input: str) -> None:
        """Process one user turn through the agentic loop."""
        # ── Build context ──────────────────────────────────────────────────
        # Only search for relevant files on task messages (not chat)
        if _needs_tools(user_input):
            relevant = self._find_relevant_files(user_input)
        else:
            relevant = []

        if relevant:
            names = ", ".join(p for p, _ in relevant)
            print_info(f"Auto-loaded: {names}")
            ctx = "\n\n".join(f"<file path=\"{p}\">\n{c}\n</file>" for p, c in relevant)
            augmented = f"{user_input}\n\n<auto_context>\n{ctx}\n</auto_context>"
        else:
            augmented = user_input

        self.session.messages.append(Message(role="user", content=augmented))

        # Cache system prompt once — don't rebuild on every tool iteration
        system_prompt = self._system_prompt()

        for iteration in range(MAX_TOOL_ITERATIONS):
            assistant_content = ""
            pending_tool_calls: list[dict] = []
            usage: dict | None = None
            label = "Working" if iteration > 0 else ""
            live = Live(_StreamStatus(label), console=console, transient=True, refresh_per_second=10)
            live.start()

            if self._tools_disabled and iteration == 0 and _needs_tools(user_input):
                live.stop()
                console.print(Panel(
                    Text.assemble(
                        ("  ⚠  ", "kaicode.warning"),
                        (f"'{self.model}' doesn't support tools.\n\n", "default"),
                        ("  Switch with ", "kaicode.muted"),
                        ("/model", "bold kaicode.assistant"),
                        (" and try again.\n", "kaicode.muted"),
                    ),
                    border_style="kaicode.warning", padding=(0, 1),
                ))
                return

            # Select relevant tools (not all 13 every time)
            active_tools = (
                None if self._tools_disabled
                else _select_tools(user_input) if _needs_tools(user_input)
                else None
            )

            # Trim history to fit context window
            trimmed_messages = self._trim_messages(self.session.messages)

            # ── Stream with retry on transient errors ───────────────────────
            stream_ok = False
            for attempt in range(MAX_RETRIES + 1):
                assistant_content = ""
                pending_tool_calls = []
                usage = None
                try:
                    stream = self.provider.stream_chat(
                        messages=trimmed_messages,
                        model=self.model,
                        system=system_prompt,   # reused, not rebuilt
                        tools=active_tools,
                    )
                    async for chunk in stream:
                        if chunk.content:
                            assistant_content += chunk.content
                        if chunk.tool_call:
                            pending_tool_calls.append(chunk.tool_call)   # collect ALL, not just last
                        if chunk.usage:
                            usage = chunk.usage
                        if chunk.done:
                            break
                    stream_ok = True
                    break
                except Exception as e:
                    live.stop()
                    err = str(e)
                    if "does not support tools" in err.lower():
                        self._tools_disabled = True
                        print_info(f"'{self.model}' doesn't support tools — text-only mode.")
                        self.session.messages.pop()
                        await self.chat(user_input)
                        return
                    if "ollama error 404" in err.lower() and self.provider_name == "ollama":
                        available = await self.provider.list_models()
                        if available:
                            self.model = available[0]
                            self.session.model = self.model
                            print_error(f"Model not found. Switching to: {self.model}")
                            self.print_header()
                            self.session.messages.pop()
                            await self.chat(user_input)
                        else:
                            print_error("No Ollama models installed. Run: ollama pull llama3.2")
                        return
                    # Retry only transient failures that happened before any output
                    if (_is_transient(err) and not assistant_content
                            and not pending_tool_calls and attempt < MAX_RETRIES):
                        wait = 1.5 * (attempt + 1)
                        print_info(f"Transient error — retrying in {wait:.0f}s ({attempt + 1}/{MAX_RETRIES})…")
                        await asyncio.sleep(wait)
                        live = Live(_StreamStatus("Retrying"), console=console, transient=True, refresh_per_second=10)
                        live.start()
                        continue
                    print_error(f"Provider error: {e}")
                    return

            live.stop()
            if not stream_ok:
                return

            if usage:
                tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                self._tokens_used += tokens
                self.session.add_tokens(tokens)

            # ── Fallback: model emitted tool calls as JSON text, not natively ─
            if not pending_tool_calls and active_tools and assistant_content:
                valid = {t["function"]["name"] for t in active_tools}
                cleaned, text_calls = _extract_text_tool_calls(assistant_content, valid)
                if text_calls:
                    assistant_content = cleaned
                    pending_tool_calls = text_calls

            # ── No tools requested: plain response, end the turn ────────────
            if not pending_tool_calls:
                if assistant_content:
                    print_kai_message(assistant_content)
                    self.session.messages.append(Message(role="assistant", content=assistant_content))
                break

            # ── Plan detection: only interrupt for real numbered plans ──────
            if assistant_content and iteration == 0 and _is_real_plan(assistant_content):
                print_plan(assistant_content)
                console.print()
                console.print(Text("  Proceed with this plan? [Y/n]: ", style="bold kaicode.warning"), end="")
                try:
                    answer = await asyncio.get_event_loop().run_in_executor(None, input)
                except (KeyboardInterrupt, EOFError):
                    console.print()
                    self.session.messages.append(Message(role="assistant", content=assistant_content))
                    return
                if answer.strip().lower() in ("n", "no"):
                    print_info("Plan cancelled.")
                    self.session.messages.append(Message(role="assistant", content=assistant_content))
                    return
            elif assistant_content:
                # Short preamble before tool calls — show it, don't block
                print_kai_message(assistant_content)

            # ── Store ONE assistant message holding the text + all tool calls
            tool_calls_payload = [
                {"id": tc.get("id", ""), "type": "function",
                 "function": {"name": tc.get("name", ""),
                              "arguments": json.dumps(tc.get("input", {}))}}
                for tc in pending_tool_calls
            ]
            self.session.messages.append(Message(
                role="assistant",
                content=assistant_content,
                tool_calls=tool_calls_payload,
            ))

            # ── Execute each tool call, append a result per call ────────────
            console.print()
            for tc in pending_tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("input", {})
                tool_id   = tc.get("id", "")

                approved = await self._request_permission(tool_name, tool_args, reason=assistant_content.strip())
                if not approved:
                    result = json.dumps({"error": "User denied this action."})
                else:
                    print_tool_call(tool_name, tool_args)
                    result = self.tool_registry.call(tool_name, tool_args)
                    print_tool_result(tool_name, result)

                if tool_name in ("edit_file", "create_file"):
                    try:
                        rdata = json.loads(result)
                        if "diff" in rdata:
                            self.last_diff = rdata["diff"]
                        if rdata.get("success"):
                            verify_err = self._verify_file(tool_args.get("path", ""))
                            if verify_err:
                                print_error("Syntax check failed — feeding error back to model")
                                console.print(Text(f"  {verify_err}", style="kaicode.error"))
                                result = json.dumps({**rdata, "syntax_error": verify_err,
                                    "note": "File saved but has a syntax error. Fix it now with edit_file."})
                            else:
                                print_success("Syntax OK")
                    except json.JSONDecodeError:
                        pass

                self.session.messages.append(Message(
                    role="tool", content=result,
                    tool_results=[{"tool_use_id": tool_id, "content": result}],
                ))

    def _verify_file(self, path: str) -> str | None:
        import subprocess, sys
        ext = Path(path).suffix.lower()
        checks: dict[str, list[str]] = {
            ".py":   [sys.executable, "-m", "py_compile", path],
            ".js":   ["node", "--check", path],
            ".ts":   ["node", "--check", path],
            ".dart": ["dart", "analyze", "--fatal-infos", path],
            ".go":   ["go", "vet", path],
            ".rb":   ["ruby", "-c", path],
            ".sh":   ["bash", "-n", path],
        }
        cmd = checks.get(ext)
        if not cmd:
            return None
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=self.cwd)
            if r.returncode != 0:
                err = (r.stderr or r.stdout).strip()
                return err[:600] if err else f"Syntax check failed (exit {r.returncode})"
        except (FileNotFoundError, Exception):
            pass
        return None

    async def _request_permission(self, tool_name: str, tool_args: dict, reason: str = "") -> bool:
        if tool_name in _AUTO_APPROVE_TOOLS or tool_name in self._always_allowed:
            return True

        label  = _TOOL_ACTION_LABELS.get(tool_name, tool_name)
        detail = _format_permission_detail(tool_name, tool_args)

        body = Text()
        body.append("  What:  ", style="bold cyan")
        body.append(f"{label}\n", style="bold white")
        body.append("  Action: ", style="bold cyan")
        body.append(f"{detail}\n", style="yellow")

        if reason:
            sentences = reason.replace("\n", " ").split(". ")
            short = ". ".join(sentences[:2]).strip()
            if len(short) > 200:
                short = short[:200] + "…"
            body.append("\n  Why:   ", style="bold cyan")
            body.append(f"{short}\n", style="dim white")

        body.append("\n")
        body.append("  1. ", style="bold green");   body.append("Yes, do it\n")
        body.append("  2. ", style="bold red");     body.append("No, skip\n")
        body.append("  3. ", style="bold cyan");    body.append(f"Yes, always allow '{tool_name}'\n")
        body.append("  4. ", style="bold magenta"); body.append("Yes, allow ALL tools this session\n")

        console.print()
        console.print(Panel(body, title="[bold kaicode.warning] Permission required [/]",
                            border_style="kaicode.warning", padding=(0, 1)))
        console.print(Text("  Choose [1/2/3/4]: ", style="bold kaicode.assistant"), end="")

        try:
            answer = await asyncio.get_event_loop().run_in_executor(None, input)
        except (KeyboardInterrupt, EOFError):
            console.print()
            return False

        answer = answer.strip().lower()
        if answer in ("1", "y", "yes", ""):
            return True
        if answer in ("3", "a", "always"):
            self._always_allowed.add(tool_name)
            print_info(f"Always allowing '{tool_name}' this session.")
            return True
        if answer in ("4", "!"):
            self._always_allowed.update(_TOOL_ACTION_LABELS.keys())
            print_info("Always allowing all tools this session.")
            return True
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
        await self.provider.aclose()   # close the old pooled HTTP client
        self.provider_name = provider_name
        self.provider = get_provider(provider_name, self.config)
        self.model = model or self.config.get_provider(provider_name).default_model or self._default_model()
        self.session.provider = provider_name
        self.session.model = self.model
        self._tools_disabled = False
        print_success(f"Switched to: {provider_name} / {self.model}")
        self.print_header()

    def clear_history(self) -> None:
        self.session.messages.clear()
        self._tokens_used = 0
        self.last_diff = ""
        print_info("Conversation cleared.")

    def save_session(self, name: str | None = None) -> None:
        print_success(f"Session saved: {self.session.save(name)}")

    def load_session(self, name: str) -> None:
        try:
            self.session = Session.load(name)
            self.provider_name = self.session.provider
            self.provider = get_provider(self.provider_name, self.config)  # old client GC'd
            self.model = self.session.model
            self._tokens_used = self.session.total_tokens
            print_success(f"Loaded session '{name}' ({len(self.session.messages)} messages)")
            self.print_header()
        except FileNotFoundError:
            print_error(f"Session not found: {name}")

    @property
    def tokens_used(self) -> int:
        return self._tokens_used
