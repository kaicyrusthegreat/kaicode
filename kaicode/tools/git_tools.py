"""Git tools for the KaiCode agent."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _run_git(args: list[str], cwd: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Git command timed out"}
    except FileNotFoundError:
        return {"error": "git not found in PATH"}
    except Exception as e:
        return {"error": str(e)}


def git_status(path: str = ".") -> dict[str, Any]:
    """Show git status of the repository."""
    result = _run_git(["status", "--porcelain", "-b"], cwd=path)
    if "error" in result:
        return result

    if result["returncode"] != 0:
        return {"error": result["stderr"] or "Not a git repository"}

    lines = result["stdout"].strip().splitlines()
    branch = ""
    staged = []
    unstaged = []
    untracked = []

    for line in lines:
        if line.startswith("##"):
            parts = line[3:].split("...")
            branch = parts[0].strip()
        elif len(line) >= 2:
            xy = line[:2]
            fname = line[3:]
            if xy[0] != " " and xy[0] != "?":
                staged.append({"status": xy[0], "file": fname})
            if xy[1] != " " and xy[1] != "?":
                unstaged.append({"status": xy[1], "file": fname})
            if xy == "??":
                untracked.append(fname)

    return {
        "branch": branch,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "clean": not staged and not unstaged and not untracked,
    }


def git_commit(
    message: str,
    path: str = ".",
    add_all: bool = False,
) -> dict[str, Any]:
    """Commit staged changes (optionally stage all changes first)."""
    if add_all:
        add_result = _run_git(["add", "-A"], cwd=path)
        if add_result.get("returncode", 1) != 0:
            return {"error": f"git add failed: {add_result.get('stderr', '')}"}

    result = _run_git(["commit", "-m", message], cwd=path)
    if result["returncode"] != 0:
        return {"error": result["stderr"] or result["stdout"]}

    return {
        "success": True,
        "message": message,
        "output": result["stdout"].strip(),
    }


def git_diff(path: str = ".", staged: bool = False) -> dict[str, Any]:
    """Show git diff."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    result = _run_git(args, cwd=path)
    if "error" in result:
        return result
    return {"diff": result["stdout"], "staged": staged}
