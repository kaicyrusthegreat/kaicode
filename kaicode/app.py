"""Core KaiCode application — the agentic loop."""

from __future__ import annotations

import asyncio
import json
import os
import re
import select
import sys
import termios
import time
import tty
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from kaicode.config import KaiConfig
from kaicode.checkpoint import CheckpointStack
from kaicode.pricing import estimate_cost
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
    print_change_preview,
)


MAX_TOOL_ITERATIONS = 25
MAX_HISTORY_MESSAGES = 50   # trim older messages beyond this

# Words the symbol-reference heuristic must never auto-search for — they appear
# in nearly every file (README especially), so searching them auto-loads junk.
_STOPWORD_SYMS = {
    "the", "this", "that", "these", "those", "file", "files", "code", "line",
    "lines", "function", "class", "method", "value", "error", "issue", "bug",
    "feature", "change", "changes", "thing", "stuff", "part", "name", "data",
    "text", "list", "item", "with", "from", "into", "your", "you", "and",
    "for", "all", "any", "one", "two", "new", "old", "use", "using", "make",
    "show", "add", "fix", "run", "see", "get", "set", "test", "tests",
    # Common 6+ letter English words that slip past the identifier filter and
    # pull in irrelevant files (they appear as "the message", "the result"…).
    "message", "commit", "result", "results", "sample", "sentence", "project",
    "repository", "directory", "folder", "subfolder", "subfolders", "error",
    "errors", "output", "confirm", "contents", "content", "command", "commands",
    "afterward", "argument", "arguments", "example", "examples", "exactly",
    "number", "numbers", "string", "values", "create", "created", "inside",
}

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
    # Note: do NOT trigger on bare "web" — it matches "web app"/"website" and
    # tempts weak models to fetch instead of build.
    if any(w in lower for w in ("http://", "https://", "url", "fetch the", "fetch this",
                                "documentation", "api reference", "look up online", "from the web")):
        names.add("web_fetch")
    if any(w in lower for w in ("search the web", "search online", "google", "find online",
                                "search for info", "look up online", "what is the latest")):
        names.add("web_search")
    if any(w in lower for w in ("type text", "type this", "click on", "click at", "mouse click",
                                "press key", "press enter", "press cmd", "press ctrl",
                                "screenshot", "screen capture", "take a screenshot",
                                "keyboard automation", "mouse automation")):
        names |= {"type_text", "key_press", "mouse_click", "screenshot"}
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
    r'search|find|grep|implement|add|generate|scaffold|'
    r'debug|open|script|code|program|function|class|module|'
    r'fetch|download|deploy|click|type|screenshot'
    r')\b',
    re.I,
)

# The only escape sequences JSON permits after a backslash inside a string.
_VALID_JSON_ESCAPES = set('"\\/bfnrtu')

def _sanitize_json_block(block: str) -> str:
    """Repair the not-quite-valid JSON that local models emit so json.loads
    accepts it. Two fixes:
      • raw control chars inside a string value (real newlines/tabs in a
        'content' field holding source code) → escaped;
      • INVALID escape sequences — most often \\' (a Python single-quote habit:
        "cwd: str = \\'.\\'"), which JSON rejects. The backslash is dropped,
        keeping the char, so \\' becomes a plain '. This is the single most
        common reason a model's text tool call fails to parse."""
    out: list[str] = []
    in_str = False
    esc = False          # previous char was a backslash, awaiting its escapee
    for c in block:
        if in_str:
            if esc:
                if c in _VALID_JSON_ESCAPES:
                    out.append("\\")
                    out.append(c)
                else:
                    # Invalid JSON escape (e.g. \') — drop the backslash, keep c.
                    out.append(c)
                esc = False
            elif c == "\\":
                # Defer: decide whether to keep the backslash once we see what it
                # is escaping (so we can strip it for invalid escapes like \').
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
    if esc:           # trailing lone backslash at end of block — drop it
        pass
    return "".join(out)


_HEREDOC_RE = re.compile(
    r'(create_file|write_file|edit_file)\s+(\S+?)\s*<<\s*[\'"]?(\w+)[\'"]?\s*\n(.*?)\n\3\b',
    re.S,
)

def _extract_heredoc_calls(content: str, valid_names: set[str]) -> tuple[str, list[dict]]:
    """Parse shell-heredoc style tool calls some models emit:
        create_file path <<EOF
        ...content...
        EOF
    """
    calls: list[dict] = []
    def _repl(m: "re.Match") -> str:
        name = m.group(1)
        if name == "write_file":
            name = "create_file"
        if name not in valid_names:
            return m.group(0)
        path, body = m.group(2).strip().strip('"\''), m.group(4)
        calls.append({
            "id": f"hd_{len(calls)}",
            "name": name,
            "input": {"path": path, "content": body},
        })
        return ""
    cleaned = _HEREDOC_RE.sub(_repl, content)
    return cleaned, calls


def _extract_text_tool_calls(content: str, valid_names: set[str]) -> tuple[str, list[dict]]:
    """Fallback: parse tool calls that a model emitted as JSON text instead of
    using the native tool-calling channel (very common with local models).

    Returns (cleaned_content, tool_calls). Each tool call is {id, name, input}.
    """
    # First handle shell-heredoc style (reasoning models like deepseek-r1)
    heredoc_calls: list[dict] = []
    if "<<" in content:
        content, heredoc_calls = _extract_heredoc_calls(content, valid_names)

    if not content or "{" not in content:
        return content, heredoc_calls

    calls: list[dict] = list(heredoc_calls)
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
                    "id": f"text_{uuid.uuid4().hex[:8]}",
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


_THINK_BLOCK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)
# Some models use other delimiters for chain-of-thought; treat them the same.
_THINK_OPEN_RE = re.compile(r'<think>|<thinking>|◁think▷', re.I)
_THINK_CLOSE_RE = re.compile(r'</think>|</thinking>|◁/think▷', re.I)


def _strip_reasoning(text: str) -> str:
    """Remove a reasoning model's chain-of-thought so only the final answer is
    shown. Handles the three shapes local 'thinking' models actually emit:

        <think>…</think> answer     well-formed block
        …reasoning… </think> answer  OPENING TAG MISSING (the model/template
                                     started already 'inside' the think block —
                                     this is the case that used to leak the whole
                                     monologue into the reply)
        <think>… (no close yet)      unclosed block mid-stream — nothing to show
    """
    text = _THINK_BLOCK_RE.sub('', text)
    # A dangling close tag means everything before it was hidden reasoning that
    # never got an opening tag — drop up to and including the last close tag.
    m = None
    for m in _THINK_CLOSE_RE.finditer(text):
        pass
    if m:
        text = text[m.end():]
    # An unclosed opening tag means we're still mid-reasoning — drop from it on.
    om = _THINK_OPEN_RE.search(text)
    if om:
        text = text[:om.start()]
    return text.strip()


def _needs_tools(message: str) -> bool:
    msg = message.strip()
    # A short, genuine question ("What features could we ADD?", "How do I
    # CREATE X?") is informational even though it contains action-verb nouns.
    # This must be checked BEFORE _HAS_TASK, whose verb list would otherwise
    # match those nouns and misroute the question through the tool path.
    # (_EXPLAIN_REQUEST is question-starters only — not the bare ack words in
    # _CHAT_RE like "ok"/"sure", which legitimately precede a task.)
    if _EXPLAIN_REQUEST.match(msg) and len(msg) < 120:
        return False
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


# A request that asks for real work to happen (build/create/fix...), as opposed
# to a question (explain/what/how...). Used to detect the #1 local-model failure:
# the model *describes* the work or dumps code in chat but never calls a tool.
_ACTION_REQUEST = re.compile(
    r'\b(create|creat|make|making|build|add|implement|writ|generat|scaffold|'
    r'set ?up|fix|refactor|rename|delete|remove|update|edit|run|install|deploy|'
    r'organi[sz]e|move|copy|sort|put|place|convert|rewrite|replace|split|merge|'
    r'extract|download|configure|format|clean|optimi[sz]e|append|insert|mark|'
    r'change|modify|migrate|rename|wrap|commit|push|execute)\b',
    re.I,
)
_EXPLAIN_REQUEST = re.compile(
    r'^\s*(explain|what|what\'s|how|why|who|when|where|describe|tell me|'
    r'can you explain|show me how|is |are |does |do |should )',
    re.I,
)


def _talked_instead_of_acting(user_input: str, content: str) -> bool:
    """True when the user asked for real work but the model replied with prose
    (often a ``` code block) and made NO tool calls — so nothing happened.

    A specific action verb (create/move/refactor/…) is the strongest signal, but
    the verb list can never be exhaustive ("transpile this", "tidy up these"…).
    So we also treat any non-question, task-shaped request (one _needs_tools
    already flagged) that came back as pure prose as a likely no-op. The caller
    guards this to fire at most once per turn, so a false positive costs only a
    single extra nudge — far cheaper than silently doing nothing."""
    if not content.strip():
        return False
    if _EXPLAIN_REQUEST.match(user_input.strip()):
        return False
    return bool(_ACTION_REQUEST.search(user_input)) or _needs_tools(user_input)


# A tool call written as JSON text: {"name": "edit_file", ...}. We look for the
# name/tool/function key pointing at a real tool. If this shape is present but the
# turn produced NO executed tool calls, the model emitted a tool call that failed
# to parse (almost always invalid JSON — unescaped " or \ inside a string value,
# e.g. code or triple-quotes in `content`). It needs a JSON-specific correction,
# not the generic "you only talked" nudge.
_TOOLCALL_SHAPE_RE = re.compile(r'"(?:name|tool|function)"\s*:\s*"([a-zA-Z_][\w]*)"')

def _has_unparsed_tool_call(content: str, valid_names: set[str]) -> bool:
    if not content or "{" not in content:
        return False
    return any(m.group(1) in valid_names for m in _TOOLCALL_SHAPE_RE.finditer(content))

# Substrings that indicate a retryable, transient provider failure
_TRANSIENT_MARKERS = (
    "429", "500", "502", "503", "504",
    "timeout", "timed out", "connect", "overloaded",
    "temporarily", "rate limit", "read error", "remote protocol",
    "model output error", "both be empty",  # Ollama sometimes returns empty output
)

def _is_transient(err: str) -> bool:
    low = err.lower()
    return any(m in low for m in _TRANSIENT_MARKERS)

MAX_RETRIES = 2


# ── ESC-to-cancel helper ──────────────────────────────────────────────────────

class _CancelFlag:
    """Thread-safe ESC-to-cancel during streaming.

    The listener uses cbreak mode (not raw): cbreak turns off canonical input
    and echo — enough to read ESC a character at a time — but LEAVES output
    processing (OPOST/ONLCR) on. Raw mode disables ONLCR, which breaks the
    newline→CRLF translation that Rich's Live relies on to reposition the
    cursor; with it off, every Live refresh is appended below the last instead
    of overwriting it, producing the repeated-frame 'staircase' ghosting.
    stop() still joins the thread and restores the terminal synchronously
    before any panels are printed.
    """
    def __init__(self):
        self.cancelled = False
        self._thread = None
        self._fd = None
        self._old = None

    def start_listening(self):
        import threading
        self.cancelled = False
        try:
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
        except Exception:
            self._fd = None
            self._old = None
            return  # not a real terminal — ESC-cancel simply disabled
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self):
        try:
            # cbreak (not setraw) — keeps OPOST/ONLCR on so Rich's Live can
            # redraw in place instead of ghosting frame after frame.
            tty.setcbreak(self._fd, termios.TCSANOW)
            while not self.cancelled:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    if sys.stdin.read(1) == '\x1b':  # ESC
                        self.cancelled = True
                        break
        except Exception:
            pass
        finally:
            self._restore()

    def _restore(self):
        if self._fd is not None and self._old is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
            except Exception:
                pass

    def stop(self):
        self.cancelled = True
        t, self._thread = self._thread, None
        if t is not None:
            t.join(timeout=0.3)      # wait for the listener to leave raw mode
        self._restore()              # guarantee cooked mode before any printing


# ── Permission helpers ────────────────────────────────────────────────────────

# Read-only tools are safe (and sometimes sensible) to repeat verbatim, so the
# stuck-loop guard ignores them; it only fires on state-changing calls.
_READONLY_TOOLS = {
    "read_file", "list_files", "search_files", "grep_ast", "repo_map",
    "git_status", "git_diff", "web_fetch", "web_search",
}

_AUTO_APPROVE_TOOLS = {
    "read_file", "list_files", "search_files",
    "git_status", "git_diff",
    "grep_ast",      # read-only symbol search
    "web_fetch",     # read-only URL fetch
    "web_search",    # read-only web search
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
    "type_text":        "Type text (keyboard)",
    "key_press":        "Press keys",
    "mouse_click":      "Mouse click",
    "screenshot":       "Take screenshot",
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
    """Phase spinner shown while the model generates.

    Displays only a rotating phase header ('Thinking… (3s)') for the duration of
    generation — it deliberately does NOT echo the streamed tokens live (no
    'typing' effect). The completed reply is rendered once, as a polished panel,
    by print_kai_message after streaming finishes. self.raw is still accumulated
    so the phase can read as 'Thinking' while the model is inside a <think> block.
    """
    _PHASES = ["Thinking", "Reasoning", "Deciphering", "Processing"]

    def __init__(self, label: str = "") -> None:
        self._start = time.monotonic()
        self._label = label
        self.raw = ""            # live-updated with the accumulated response

    def _elapsed(self) -> int:
        return int(time.monotonic() - self._start)

    def _header(self, phase: str) -> Text:
        t = Text()
        t.append("  ✽ ", style="kaicode.assistant")
        t.append(f"{phase}… ", style="kaicode.info")
        t.append(f"({self._elapsed()}s)", style="kaicode.muted")
        return t

    def _visible(self) -> tuple[str, bool]:
        """Return (text-to-show, still_inside_a_think_block)."""
        # Still thinking when an opening tag has no matching close after it,
        # i.e. there are more opens than closes.
        opens = len(_THINK_OPEN_RE.findall(self.raw))
        closes = len(_THINK_CLOSE_RE.findall(self.raw))
        thinking = opens > closes
        return _strip_reasoning(self.raw), thinking

    def __rich__(self) -> Text:
        # Only ever show the phase spinner — never the streamed tokens, so there
        # is no live 'typing' effect. The final reply prints once, afterward.
        _, thinking = self._visible()
        elapsed = self._elapsed()
        phase = self._label or (
            "Thinking" if thinking
            else self._PHASES[min(elapsed // 6, len(self._PHASES) - 1)]
        )
        return self._header(phase)


# ── Main application ──────────────────────────────────────────────────────────

class KaiApp:
    def __init__(self, config: KaiConfig, provider_name: str | None = None, model: str | None = None) -> None:
        self.config = config
        self.provider_name = provider_name or config.default_provider
        try:
            self.provider: BaseProvider = get_provider(self.provider_name, config)
        except (ImportError, ValueError) as e:
            # Default provider unavailable (e.g. 'cyrusago' package or Ollama not
            # present) — fall back to ollama so kaicode still launches.
            print_info(f"'{self.provider_name}' unavailable ({e}); falling back to ollama.")
            self.provider_name = "ollama"
            self.provider = get_provider("ollama", config)
        self.model = model or config.get_provider(self.provider_name).default_model or self._default_model()
        self.cwd = os.getcwd()
        self.session = Session(
            name="", provider=self.provider_name, model=self.model, cwd=self.cwd,
        )
        self.project_info = detect_project(self.cwd)
        self.tool_registry = ToolRegistry(cwd=self.cwd)
        self.last_diff: str = ""
        self._tokens_used: int = 0
        self._cost: float = 0.0
        self._always_allowed: set[str] = set()
        self._tools_disabled: bool = False
        self.checkpoints = CheckpointStack()   # undo/redo of agent file changes

    def _default_model(self) -> str:
        defaults = {
            "ollama": "qwen3:8b",
            "openai": "model-sonnet-4-6",
            "openai": "gpt-4o",
            "groq": "llama-3.1-70b-versatile",
            "openai_compat": "default",
            "cyrusago": "cyrusago",
        }
        return defaults.get(self.provider_name, "default")

    def print_header(self) -> None:
        print_header(self.model, self.provider_name, self.cwd)

    def _system_prompt(self) -> str:
        return build_system_prompt(self.project_info, self.config.system_prompt, model=self.model)

    def _trim_messages(self, messages: list[Message]) -> list[Message]:
        """Keep history within MAX_HISTORY_MESSAGES, never split mid-tool-call."""
        if len(messages) <= MAX_HISTORY_MESSAGES:
            return messages
        trimmed = messages[-MAX_HISTORY_MESSAGES:]
        # Don't start on a tool result — shift until we find user/assistant
        while trimmed and trimmed[0].role == "tool":
            trimmed = trimmed[1:]
        return trimmed

    def _resolve(self, path: str) -> str:
        """Resolve a possibly-relative tool path against the session cwd."""
        return str((Path(self.cwd) / path).expanduser())

    _MENTION_RE = re.compile(r'(?:^|\s)@([^\s@]+)')

    @staticmethod
    def _clip(text: str, limit: int, rel_path: str) -> str:
        """Clip auto-loaded file content to `limit` chars. If the file is longer,
        append an explicit truncation marker — otherwise the model treats the
        partial snippet as the whole file and crafts edit_file `old_content` that
        can never match the real (unseen) text, looping on 'old_content not found'.
        The marker tells it to read_file for exact contents before editing."""
        if len(text) <= limit:
            return text
        return (
            text[:limit]
            + f"\n\n… [TRUNCATED — showing first {limit} of {len(text)} chars of "
            f"{rel_path}. This is NOT the full file. Call read_file(\"{rel_path}\") "
            f"to get the exact, complete contents before editing it.]"
        )

    def _expand_mentions(self, text: str) -> list[tuple[str, str]]:
        """Explicit @path mentions → (path, content). User-directed and reliable,
        unlike the fuzzy auto-detect; takes precedence when present."""
        found: dict[str, str] = {}
        for raw in self._MENTION_RE.findall(text):
            cand = raw.rstrip('.,;:!?)')
            p = (Path(self.cwd) / cand).expanduser()
            try:
                if p.is_file() and p.stat().st_size < 200_000:
                    found[cand] = self._clip(
                        p.read_text("utf-8", errors="replace"), 8000, cand)
            except Exception:
                pass
        return list(found.items())

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
        # Drop common English words — searching the repo for "the"/"this"/"file"
        # matches almost everything (especially README), which is why unrelated
        # tasks kept auto-loading README.md. Keep only identifier-looking tokens.
        sym_refs = [
            s for s in sym_refs
            if s.lower() not in _STOPWORD_SYMS
            and (any(c.isupper() for c in s[1:]) or "_" in s or len(s) >= 6)
        ]

        def _read(rel_path: str) -> str | None:
            p = Path(self.cwd) / rel_path
            if p.is_file() and p.stat().st_size < 200_000:
                return self._clip(
                    p.read_text("utf-8", errors="replace"), MAX_CHARS, rel_path)
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
        # Compute intent / tool selection ONCE — user_input is constant for the
        # whole turn, so there's no reason to recompute these every iteration.
        needs_tools = _needs_tools(user_input)
        base_tools = _select_tools(user_input) if needs_tools else None

        # ── Build context ──────────────────────────────────────────────────
        # Explicit @path mentions win — they're precise and user-directed. Only
        # fall back to the fuzzy repo search (off the event loop, hard timeout —
        # a big repo must never freeze the UI before the model is contacted)
        # when the user didn't point at anything themselves.
        mentions = self._expand_mentions(user_input)
        if mentions:
            relevant = mentions
        elif needs_tools:
            try:
                relevant = await asyncio.wait_for(
                    asyncio.to_thread(self._find_relevant_files, user_input),
                    timeout=2.5,
                )
            except (asyncio.TimeoutError, Exception):
                relevant = []
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

        cancel = _CancelFlag()
        tools_nudged = False   # have we already pushed the model to actually act?
        did_act = False        # did ANY tool execute during this turn?
        last_action_key = None # last state-changing call, to catch stuck loops

        for iteration in range(MAX_TOOL_ITERATIONS):
            assistant_content = ""
            pending_tool_calls: list[dict] = []
            usage: dict | None = None
            label = "Working" if iteration > 0 else ""
            status = _StreamStatus(label)
            live = Live(status, console=console, transient=True, refresh_per_second=10)
            live.start()

            # ESC listener is active ONLY while streaming (raw mode would
            # otherwise corrupt panel rendering during printing).
            cancel.start_listening()

            # Tools were selected once at the top of the turn (constant input).
            active_tools = None if self._tools_disabled else base_tools

            # Trim history to fit context window
            trimmed_messages = self._trim_messages(self.session.messages)

            # ── Stream with retry on transient errors ───────────────────────
            stream_ok = False
            for attempt in range(MAX_RETRIES + 1):
                assistant_content = ""
                pending_tool_calls = []
                usage = None
                status.raw = ""
                try:
                    stream = self.provider.stream_chat(
                        messages=trimmed_messages,
                        model=self.model,
                        system=system_prompt,   # reused, not rebuilt
                        tools=active_tools,
                    )
                    async for chunk in stream:
                        # ── Check ESC cancel ─────────────────────────────
                        if cancel.cancelled:
                            live.stop()
                            cancel.stop()
                            if assistant_content.strip():
                                print_kai_message(assistant_content.strip() + "\n\n⚡ *cancelled*")
                                self.session.messages.append(
                                    Message(role="assistant", content=assistant_content))
                            else:
                                print_info("Cancelled.")
                            return
                        if chunk.content:
                            assistant_content += chunk.content
                            status.raw = assistant_content   # live-stream to screen
                        if chunk.tool_call:
                            pending_tool_calls.append(chunk.tool_call)
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
                        print_info(f"'{self.model}' doesn't support native tools — using text-based tool calls.")
                        # Don't return — just retry this iteration without native tools
                        active_tools = None
                        status = _StreamStatus(label)
                        live = Live(status, console=console, transient=True, refresh_per_second=10)
                        live.start()
                        continue
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
                        status = _StreamStatus("Retrying")
                        live = Live(status, console=console, transient=True, refresh_per_second=10)
                        live.start()
                        continue
                    print_error(f"Provider error: {e}")
                    return

            live.stop()
            cancel.stop()   # leave raw mode BEFORE any panel/printing this turn
            if not stream_ok:
                return

            if usage:
                self._record_usage(usage)

            # ── Strip chain-of-thought from reasoning models ──────────────
            if assistant_content:
                assistant_content = _strip_reasoning(assistant_content)

            # ── Fallback: model emitted tool calls as JSON text, not natively ─
            # Always scan: a model may mix one native call with extra text calls.
            # For models without native tool support, this is the PRIMARY mechanism.
            if assistant_content and (active_tools or self._tools_disabled):
                if active_tools:
                    valid = {t["function"]["name"] for t in active_tools}
                else:
                    # Tools-disabled mode: accept any known tool name
                    valid = {t["function"]["name"] for t in TOOL_DEFINITIONS}
                cleaned, text_calls = _extract_text_tool_calls(assistant_content, valid)
                if text_calls:
                    assistant_content = cleaned
                    # Merge, skipping any that duplicate a native call
                    seen = {(c.get("name"), json.dumps(c.get("input"), sort_keys=True))
                            for c in pending_tool_calls}
                    for c in text_calls:
                        key = (c.get("name"), json.dumps(c.get("input"), sort_keys=True))
                        if key not in seen:
                            pending_tool_calls.append(c)
                            seen.add(key)

            # ── No tool calls this turn ─────────────────────────────────────
            if not pending_tool_calls:
                cancel.stop()
                # Failure mode (common with small local models): the user asked us
                # to build/create/fix something, but the model just *described* it
                # or dumped code in a ``` block and called no tools — so nothing
                # actually happened. Push it once to use the tools for real.
                # Crucially, only nudge when NOTHING ran this whole turn: once any
                # tool has executed, a final text-only message is the model's
                # legitimate closing summary, not a failure — re-nudging there
                # makes it redundantly redo (and possibly clobber) finished work.
                # Did the model TRY to call a tool as JSON text that failed to
                # parse? (Distinct from "only talked": here it intended to act but
                # emitted invalid JSON, so it needs a JSON-specific correction.)
                _all_names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
                malformed_call = _has_unparsed_tool_call(assistant_content, _all_names)

                if (needs_tools and not tools_nudged
                        and (malformed_call
                             or (not did_act
                                 and _talked_instead_of_acting(user_input, assistant_content)))):
                    tools_nudged = True
                    if assistant_content:
                        print_kai_message(assistant_content)
                        self.session.messages.append(
                            Message(role="assistant", content=assistant_content))
                    if malformed_call:
                        nudge = (
                            "Your last message contained a tool call written as JSON "
                            "text, but it was NOT valid JSON, so it could not be "
                            "executed and nothing happened. The usual cause is "
                            "unescaped characters inside a string value — every \" "
                            "inside a value must be written \\\", every newline \\n, "
                            "and every backslash \\\\ (this bites when `content`/"
                            "`new_content` holds code, quotes, or triple-quotes). "
                            "Re-issue the call NOW. Strongly prefer the native "
                            "tool-calling format; if you must write JSON, make it "
                            "strictly valid and put the whole call in ONE object."
                        )
                        nudge_note = "Tool call was invalid JSON — asking the model to re-issue it…"
                    else:
                        nudge = (
                            "You described the work but did NOT do it — nothing was "
                            "actually created or changed. Code written in chat does "
                            "nothing; the user cannot see or use it. Use the tools NOW "
                            "to do the real work: call create_file (one call per file, "
                            "with the COMPLETE content), edit_file, create_directory, "
                            "and run_command as needed. Do not paste file contents as "
                            "text — emit the tool calls."
                        )
                        nudge_note = "No files were created — telling the model to use its tools…"
                    self.session.messages.append(Message(role="user", content=nudge))
                    print_info(nudge_note)
                    continue
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

            # (Whether the model actually CHANGED anything is decided per tool
            # below, after each call runs — see `did_act`. A non-readonly call that
            # ERRORS, is denied, or is a no-op must not count, or the model could
            # read a file, fail an edit, then summarize and never get nudged.)

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

                # ── Stuck-loop guard ────────────────────────────────────────
                # If the model repeats the EXACT same state-changing call it just
                # made — with no other action in between — re-running it can't
                # produce a different result. Don't execute it again; tell the
                # model so plainly and make it change tack. (edit→run→edit→run is
                # unaffected: those keys differ, so this only trips true repeats.)
                action_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                if tool_name not in _READONLY_TOOLS and action_key == last_action_key:
                    result = json.dumps({
                        "error": "Duplicate call — you just ran this exact same "
                        "operation and nothing changed in between, so the result is "
                        "identical. Repeating it will not help. Either try a "
                        "DIFFERENT command/approach, fix the underlying problem "
                        "first, or stop and report what you found.",
                    })
                    print_error("Skipped a repeated identical call (stuck-loop guard)")
                    self.session.messages.append(Message(
                        role="tool", content=result,
                        tool_results=[{"tool_use_id": tool_id, "content": result}],
                    ))
                    continue

                is_write = tool_name in ("edit_file", "create_file")
                target = self._resolve(tool_args.get("path", "")) if is_write else ""
                before = CheckpointStack.snapshot(target) if is_write else None

                # Show the change (diff / new contents) BEFORE asking to apply it,
                # so the user reviews what will happen — like KaiCode.
                if is_write and tool_name not in self._always_allowed:
                    print_change_preview(tool_name, tool_args, self.cwd)

                approved = await self._request_permission(tool_name, tool_args, reason=assistant_content.strip())
                if not approved:
                    result = json.dumps({"error": "User denied this action."})
                else:
                    print_tool_call(tool_name, tool_args)
                    # Tools do blocking file IO / subprocesses (run_command can
                    # take 30s) — run them in a worker thread so the event loop
                    # stays responsive.
                    result = await asyncio.to_thread(
                        self.tool_registry.call, tool_name, tool_args)
                    print_tool_result(tool_name, result)

                if is_write:
                    try:
                        rdata = json.loads(result)
                        if "diff" in rdata:
                            self.last_diff = rdata["diff"]
                        if rdata.get("success"):
                            # Checkpoint the change so /undo can revert it exactly.
                            saved_path = rdata.get("path") or target
                            after = CheckpointStack.snapshot(saved_path)
                            self.checkpoints.record(saved_path, before, after, tool_name)
                            verify_err = await asyncio.to_thread(
                                self._verify_file, tool_args.get("path", ""))
                            if verify_err:
                                print_error("Syntax check failed — feeding error back to model")
                                console.print(Text(f"  {verify_err}", style="kaicode.error"))
                                result = json.dumps({**rdata, "syntax_error": verify_err,
                                    "note": "File saved but has a syntax error (see "
                                    "syntax_error). Fix it by RE-CREATING the whole file "
                                    "correctly with create_file (it overwrites). Do NOT "
                                    "patch it with edit_file/replace_all — that tends to "
                                    "corrupt the file. Write the complete corrected "
                                    "content in ONE create_file call."})
                            else:
                                print_success("Syntax OK")
                    except json.JSONDecodeError:
                        pass

                if tool_name not in _READONLY_TOOLS:
                    last_action_key = action_key
                    # "Acted" = a state-changing tool actually ran without erroring.
                    # A failed edit (old_content not found), a denied call, or the
                    # duplicate-guard no-op all return an "error" and changed
                    # nothing — they must NOT suppress the "talked instead of
                    # acting" nudge. (Non-JSON results are rare; treat as acted.)
                    try:
                        if "error" not in json.loads(result):
                            did_act = True
                    except (ValueError, TypeError):
                        did_act = True

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
        self._cost = 0.0
        self.last_diff = ""
        print_info("Conversation cleared.")

    # ── Checkpoint / undo ──────────────────────────────────────────────────
    def _rel(self, path: str) -> str:
        try:
            return str(Path(path).resolve().relative_to(Path(self.cwd).resolve()))
        except Exception:
            return path

    def undo(self) -> None:
        ch = self.checkpoints.undo()
        if ch is None:
            print_info("Nothing to undo.")
            return
        verb = {"created": "Removed created", "deleted": "Restored deleted",
                "edited": "Reverted"}.get(ch.label, "Reverted")
        print_success(f"{verb} {self._rel(ch.path)}")

    def redo(self) -> None:
        ch = self.checkpoints.redo()
        if ch is None:
            print_info("Nothing to redo.")
            return
        print_success(f"Re-applied change to {self._rel(ch.path)}")

    def list_changes(self) -> None:
        history = self.checkpoints.history()
        if not history:
            print_info("No file changes this session.")
            return
        print_info(f"{len(history)} change(s) this session (newest last):")
        for ch in history:
            console.print(
                f"  [kaicode.muted]{ch.label:>7}[/]  [kaicode.dir]{self._rel(ch.path)}[/]"
            )

    def save_session(self, name: str | None = None) -> None:
        print_success(f"Session saved: {self.session.save(name)}")

    def load_session(self, name: str) -> None:
        try:
            self.session = Session.load(name)
            self.provider_name = self.session.provider
            self.provider = get_provider(self.provider_name, self.config)  # old client GC'd
            self.model = self.session.model
            self._tokens_used = self.session.total_tokens
            self._cost = self.session.total_cost
            print_success(f"Loaded session '{name}' ({len(self.session.messages)} messages)")
            self.print_header()
        except FileNotFoundError:
            print_error(f"Session not found: {name}")

    def _record_usage(self, usage: dict) -> None:
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        self._tokens_used += p + c
        self.session.add_tokens(p + c)
        cost = estimate_cost(self.provider_name, self.model, p, c)
        if cost:
            self._cost += cost
            self.session.add_cost(cost)

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def cost_estimate(self) -> float:
        return self._cost

    # ── Goal mode: work → verify with tests → feed failures back → retry ──
    async def run_goal(self, goal: str, max_attempts: int = 5) -> None:
        """Autonomous loop toward a stated goal, verified by the test suite.

        Each attempt is one full agentic turn. Afterwards run_tests decides:
        pass → done; fail → the failure output becomes the next prompt. When
        no test suite exists, verification is impossible — one attempt runs
        and the user is told it went unverified."""
        print_info(f"Goal: {goal}  (max {max_attempts} attempts)")
        prompt = (
            f"GOAL: {goal}\n\n"
            "Work toward this goal using your tools until it is achieved. "
            "Make the necessary changes, then run the test suite with run_tests "
            "to verify. If tests fail, fix the failures and run them again. "
            "Do not stop at describing changes — actually make them."
        )
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                print_info(f"Attempt {attempt}/{max_attempts}")
            await self.chat(prompt)

            result_raw = await asyncio.to_thread(self.tool_registry.call, "run_tests", {})
            try:
                result = json.loads(result_raw)
            except (ValueError, TypeError):
                result = {"error": "unreadable test result"}

            if "error" in result:
                # No test suite (or runner failure) — can't verify automatically.
                print_info(f"Could not verify goal automatically: {result['error']}")
                return
            if result.get("passed"):
                print_success(f"Goal verified — test suite passed (attempt {attempt}/{max_attempts}).")
                return

            print_error(f"Tests still failing after attempt {attempt}/{max_attempts}.")
            if attempt == max_attempts:
                break
            output = (result.get("output") or "")[:3000]
            prompt = (
                f"The goal is NOT met yet — the test suite still fails. "
                f"Test command: {result.get('command', '?')}\n\n"
                f"Failure output:\n{output}\n\n"
                "Analyze the failures, fix the code with your tools, and run "
                "run_tests again until everything passes."
            )
        print_error(f"Goal not reached within {max_attempts} attempts. "
                    "Review the test output above or continue interactively.")

    # ── AI commit message ──────────────────────────────────────────────────
    async def ai_commit(self) -> None:
        """Generate a conventional commit message from the current diff,
        confirm with the user, then commit all changes."""
        status_raw = await asyncio.to_thread(self.tool_registry.call, "git_status", {})
        try:
            status = json.loads(status_raw)
        except (ValueError, TypeError):
            status = {"error": "unreadable git status"}
        if "error" in status:
            print_error(status["error"])
            return
        if status.get("clean"):
            print_info("Nothing to commit — working tree clean.")
            return

        diff = ""
        for staged in (True, False):
            raw = await asyncio.to_thread(
                self.tool_registry.call, "git_diff", {"staged": staged})
            try:
                diff += json.loads(raw).get("diff", "")
            except (ValueError, TypeError):
                pass
        untracked = status.get("untracked", [])
        if untracked:
            diff += "\n\nNew (untracked) files:\n" + "\n".join(untracked[:30])
        if not diff.strip():
            print_info("No diff content found to describe.")
            return

        prompt = (
            "Write a git commit message for the changes below. Use the "
            "conventional-commit style when it fits (feat:/fix:/refactor:/docs:…). "
            "First line under 72 characters; add a short body only if the change "
            "is complex. Respond with ONLY the commit message — no quotes, no "
            "code fences, no commentary.\n\n"
            f"{diff[:6000]}"
        )

        print_info("Generating commit message…")
        message = ""
        usage: dict | None = None
        try:
            stream = self.provider.stream_chat(
                messages=[Message(role="user", content=prompt)],
                model=self.model, system="", tools=None,
            )
            async for chunk in stream:
                if chunk.content:
                    message += chunk.content
                if chunk.usage:
                    usage = chunk.usage
                if chunk.done:
                    break
        except Exception as e:
            print_error(f"Provider error: {e}")
            return
        if usage:
            self._record_usage(usage)

        message = _strip_reasoning(message).strip().strip("`\"' ")
        if not message:
            print_error("Model returned an empty commit message.")
            return

        console.print()
        console.print(Panel(Text(message), title="[bold kaicode.assistant] Commit message [/]",
                            border_style="kaicode.separator", padding=(0, 1)))
        console.print(Text("  Commit ALL changes with this message? [Y/n/e(dit)]: ",
                           style="bold kaicode.warning"), end="")
        try:
            answer = await asyncio.get_event_loop().run_in_executor(None, input)
        except (KeyboardInterrupt, EOFError):
            console.print()
            return
        answer = answer.strip().lower()
        if answer in ("n", "no"):
            print_info("Commit cancelled.")
            return
        if answer in ("e", "edit"):
            console.print(Text("  Enter commit message: ", style="bold kaicode.assistant"), end="")
            try:
                edited = await asyncio.get_event_loop().run_in_executor(None, input)
            except (KeyboardInterrupt, EOFError):
                console.print()
                return
            if edited.strip():
                message = edited.strip()

        result_raw = await asyncio.to_thread(
            self.tool_registry.call, "git_commit",
            {"message": message, "add_all": True})
        try:
            result = json.loads(result_raw)
        except (ValueError, TypeError):
            result = {"error": result_raw}
        if result.get("success"):
            print_success(result.get("output", "Committed."))
        else:
            print_error(str(result.get("error", "Commit failed.")))
