"""Tool registry mapping tool names to implementations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from kaicode.tools.file_tools import (
    read_file,
    edit_file,
    create_file,
    create_directory,
    list_files,
    run_command,
)
from kaicode.tools.search_tools import search_files
from kaicode.tools.git_tools import git_status, git_commit, git_diff
from kaicode.tools.memory_tools import update_memory
from kaicode.tools.ast_tools import grep_ast
from kaicode.tools.web_tools import web_fetch
from kaicode.tools.web_search_tools import web_search
from kaicode.tools.test_tools import run_tests
from kaicode.tools.repo_map_tools import repo_map
from kaicode.tools.keyboard_mouse_tools import type_text, key_press, mouse_click, screenshot


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this to understand existing code before modifying it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "start_line": {
                        "type": "integer",
                        "description": "Start line (1-indexed, optional)",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "End line (inclusive, optional)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing exact text content. old_content must match the file's text exactly (including whitespace) and uniquely. To change every occurrence (e.g. rename a variable, change all 'TODO' to 'DONE'), set replace_all=true.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_content": {
                        "type": "string",
                        "description": "Exact text to replace (must match exactly)",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New text to put in place of old_content",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace ALL occurrences instead of just the first (default: false)",
                    },
                },
                "required": ["path", "old_content", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory (folder). Use this when the user asks to create a folder or directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file with the given content, or overwrite an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to create"},
                    "content": {"type": "string", "description": "File content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory tree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: current directory)",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Max depth to traverse (default: 2)",
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files (default: false)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for text patterns in files. Use this to find where things are defined or used.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text or regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: current directory)",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.py')",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search (default: false)",
                    },
                    "use_regex": {
                        "type": "boolean",
                        "description": "Treat pattern as regex (default: false)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (default: 50)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command. Use for running tests, builds, linters, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (default: current directory)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Show the git status of the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository path (default: current directory)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit changes to git with a message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                    "path": {
                        "type": "string",
                        "description": "Repository path (default: current directory)",
                    },
                    "add_all": {
                        "type": "boolean",
                        "description": "Stage all changes before committing (default: false)",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_memory",
            "description": (
                "Save persistent notes about this project that will be available in future sessions. "
                "Use this to remember: architecture decisions, coding conventions, important file locations, "
                "user preferences, ongoing tasks, or anything useful to recall later. "
                "The content you provide REPLACES the entire memory, so always include everything you want to keep."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full markdown content to store as project memory. Include all notes you want to persist.",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_ast",
            "description": "Search for function, class, or symbol definitions by name using AST analysis for Python and regex for other languages. More precise than search_files — finds actual definitions, not just mentions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name to find (function, class, variable)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search (default: project root)",
                    },
                    "symbol_type": {
                        "type": "string",
                        "description": "'function', 'class', or 'any' (default: 'any')",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a URL and return its text content. Use to look up documentation, package APIs, error messages, or any web resource.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters to return (default: 6000)",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the project's test suite. Auto-detects the runner (pytest, npm test, flutter test, go test, cargo test, etc.) or accepts a custom command. Always run tests after making code changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Custom test command (optional — auto-detected if omitted)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 60)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repo_map",
            "description": "Get a compact map of the whole codebase — every source file with its top-level classes and functions. Call this first when you need to understand an unfamiliar project's structure before diving into specific files.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. Use when you need to find documentation, look up errors, or get current information from the internet. Returns titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (default: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text using the keyboard. Use to enter text into applications, terminals, or text fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "interval": {
                        "type": "number",
                        "description": "Delay between keystrokes in seconds (default: 0.02)",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "key_press",
            "description": "Press a key or key combination. Examples: 'enter', 'tab', 'cmd+c', 'ctrl+shift+t'. Use '+' to combine keys.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "string",
                        "description": "Key(s) to press. Use '+' for combos: 'cmd+c', 'ctrl+z', 'enter'",
                    },
                },
                "required": ["keys"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_click",
            "description": "Click the mouse at screen coordinates. Use for GUI automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X screen coordinate"},
                    "y": {"type": "integer", "description": "Y screen coordinate"},
                    "button": {
                        "type": "string",
                        "description": "'left', 'right', or 'middle' (default: 'left')",
                    },
                    "clicks": {
                        "type": "integer",
                        "description": "Number of clicks, 2 for double-click (default: 1)",
                    },
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Take a screenshot of the entire screen and save it to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to save the screenshot (default: 'screenshot.png')",
                    },
                },
                "required": [],
            },
        },
    },
]


class ToolRegistry:
    """Maps tool names to their implementations."""

    def __init__(self, cwd: str = ".") -> None:
        self.cwd = cwd
        self.root = Path(cwd).expanduser().resolve()
        self._tools: dict[str, Callable] = {
            "read_file": self._read_file,
            "edit_file": self._edit_file,
            "create_file": self._create_file,
            "list_files": self._list_files,
            "search_files": self._search_files,
            "create_directory": self._create_directory,
            "run_command": self._run_command,
            "git_status": lambda **kw: git_status(**{"path": self.cwd, **kw}),
            "git_commit": lambda **kw: git_commit(**{"path": self.cwd, **kw}),
            "git_diff": lambda **kw: git_diff(**{"path": self.cwd, **kw}),
            "update_memory": lambda **kw: update_memory(**{"project_root": self.cwd, **kw}),
            "grep_ast": self._grep_ast,
            "web_fetch": web_fetch,
            "web_search": web_search,
            "run_tests": self._run_tests,
            "repo_map": self._repo_map,
            "type_text": type_text,
            "key_press": key_press,
            "mouse_click": mouse_click,
            "screenshot": self._screenshot,
        }

    def _resolve_workspace_path(self, raw_path: str | Path | None) -> Path | dict[str, str]:
        candidate = Path(str(raw_path or ".")).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError:
            return {"error": "Path is outside the project workspace."}
        return resolved

    def _with_scoped_path(
        self,
        func: Callable,
        kwargs: dict[str, Any],
        key: str = "path",
        default: str | None = None,
    ) -> dict[str, Any]:
        raw = kwargs.get(key, default)
        scoped = self._resolve_workspace_path(raw)
        if isinstance(scoped, dict):
            return scoped
        next_kwargs = {**kwargs, key: str(scoped)}
        return func(**next_kwargs)

    def _read_file(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(read_file, kw)

    def _edit_file(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(edit_file, kw)

    def _create_file(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(create_file, kw)

    def _create_directory(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(create_directory, kw)

    def _list_files(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(list_files, kw, default=".")

    def _search_files(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(search_files, kw, default=".")

    def _grep_ast(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(grep_ast, {"path": self.cwd, **kw}, default=".")

    def _run_tests(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(run_tests, {"path": self.cwd, **kw}, default=".")

    def _repo_map(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(repo_map, {"path": self.cwd, **kw}, default=".")

    def _run_command(self, **kw: Any) -> dict[str, Any]:
        scoped = self._resolve_workspace_path(kw.get("cwd", self.cwd))
        if isinstance(scoped, dict):
            return scoped
        next_kwargs = {**kw, "cwd": str(scoped)}
        return run_command(**next_kwargs)

    def _screenshot(self, **kw: Any) -> dict[str, Any]:
        return self._with_scoped_path(screenshot, kw, default="screenshot.png")

    # Common argument aliases models use that differ from our parameter names
    _ARG_ALIASES = {
        "cmd": "command",
        "shell": "command",
        "bash": "command",
        "script": "command",
        "file": "path",
        "filename": "path",
        "filepath": "path",
        "file_path": "path",
        "dir": "path",
        "directory": "path",
        "folder": "path",
        "query": "pattern",
        "q": "pattern",
        "regex": "pattern",
        "text": "pattern",
        "url_": "url",
        "link": "url",
        "uri": "url",
        "msg": "message",
        "commit_message": "message",
        "contents": "content",
        "body": "content",
        "data": "content",
        "old": "old_content",
        "new": "new_content",
        "old_str": "old_content",
        "new_str": "new_content",
        "old_string": "old_content",
        "new_string": "new_content",
    }

    # Tools that accept a positional-ish single string the model sometimes
    # passes under a generic key
    def _normalize_args(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(args, dict):
            return {}
        # Find this tool's real parameter names from its schema
        valid = set()
        for t in TOOL_DEFINITIONS:
            if t["function"]["name"] == name:
                valid = set(t["function"]["parameters"].get("properties", {}).keys())
                break
        out: dict[str, Any] = {}
        for k, v in args.items():
            if k in valid:
                out[k] = v
            elif (
                k in self._ARG_ALIASES
                and self._ARG_ALIASES[k] in valid
                and self._ARG_ALIASES[k] not in args
            ):
                out[self._ARG_ALIASES[k]] = v
            else:
                out[k] = v  # keep unknown keys; the tool will surface a clear error
        return out

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        if name not in self._tools:
            return json.dumps({"error": f"Unknown tool: {name}"})
        arguments = self._normalize_args(name, arguments)
        try:
            result = self._tools[name](**arguments)
            return json.dumps(result, ensure_ascii=False)
        except TypeError as e:
            return json.dumps({"error": f"Invalid arguments: {e}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
