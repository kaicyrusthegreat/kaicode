"""Tool registry mapping tool names to implementations."""

from __future__ import annotations

import json
from typing import Any, Callable

from kaicode.tools.file_tools import read_file, edit_file, create_file, create_directory, list_files, run_command
from kaicode.tools.search_tools import search_files
from kaicode.tools.git_tools import git_status, git_commit, git_diff


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
                    "start_line": {"type": "integer", "description": "Start line (1-indexed, optional)"},
                    "end_line": {"type": "integer", "description": "End line (inclusive, optional)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing exact text content. The old_content must match exactly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_content": {"type": "string", "description": "Exact text to replace (must match exactly)"},
                    "new_content": {"type": "string", "description": "New text to put in place of old_content"},
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
                    "path": {"type": "string", "description": "Directory path (default: current directory)"},
                    "depth": {"type": "integer", "description": "Max depth to traverse (default: 2)"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files (default: false)"},
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
                    "pattern": {"type": "string", "description": "Text or regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory to search in (default: current directory)"},
                    "file_pattern": {"type": "string", "description": "Glob pattern to filter files (e.g., '*.py')"},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitive search (default: false)"},
                    "use_regex": {"type": "boolean", "description": "Treat pattern as regex (default: false)"},
                    "max_results": {"type": "integer", "description": "Max results to return (default: 50)"},
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
                    "cwd": {"type": "string", "description": "Working directory (default: current directory)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
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
                    "path": {"type": "string", "description": "Repository path (default: current directory)"},
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
                    "path": {"type": "string", "description": "Repository path (default: current directory)"},
                    "add_all": {"type": "boolean", "description": "Stage all changes before committing (default: false)"},
                },
                "required": ["message"],
            },
        },
    },
]


class ToolRegistry:
    """Maps tool names to their implementations."""

    def __init__(self, cwd: str = ".") -> None:
        self.cwd = cwd
        self._tools: dict[str, Callable] = {
            "read_file": read_file,
            "edit_file": edit_file,
            "create_file": create_file,
            "list_files": list_files,
            "search_files": search_files,
            "create_directory": create_directory,
            "run_command": lambda **kw: run_command(**{"cwd": self.cwd, **kw}),
            "git_status": lambda **kw: git_status(**{"path": self.cwd, **kw}),
            "git_commit": lambda **kw: git_commit(**{"path": self.cwd, **kw}),
            "git_diff": lambda **kw: git_diff(**{"path": self.cwd, **kw}),
        }

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        if name not in self._tools:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = self._tools[name](**arguments)
            return json.dumps(result, ensure_ascii=False)
        except TypeError as e:
            return json.dumps({"error": f"Invalid arguments: {e}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
