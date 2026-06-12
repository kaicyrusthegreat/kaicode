from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from kaicode.tools.registry import ToolRegistry


class ToolRegistryWorkspaceTests(unittest.TestCase):
    def test_create_file_outside_workspace_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            registry = ToolRegistry(cwd=str(root))

            result = json.loads(
                registry.call(
                    "create_file",
                    {"path": "../outside.txt", "content": "nope"},
                )
            )

            self.assertEqual(result["error"], "Path is outside the project workspace.")
            self.assertFalse((Path(tmp) / "outside.txt").exists())

    def test_run_command_outside_workspace_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            registry = ToolRegistry(cwd=str(root))

            result = json.loads(
                registry.call(
                    "run_command",
                    {"command": "pwd", "cwd": str(Path(tmp).parent)},
                )
            )

            self.assertEqual(result["error"], "Path is outside the project workspace.")

    def test_symlink_escape_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            outside = Path(tmp) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "secret.txt").write_text("secret", encoding="utf-8")
            try:
                os.symlink(outside, root / "escape")
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            registry = ToolRegistry(cwd=str(root))
            result = json.loads(registry.call("read_file", {"path": "escape/secret.txt"}))

            self.assertEqual(result["error"], "Path is outside the project workspace.")

    def test_extra_workspace_root_allows_scoped_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            shared = Path(tmp) / "shared"
            root.mkdir()
            shared.mkdir()
            target = shared / "notes.txt"
            target.write_text("shared context", encoding="utf-8")
            registry = ToolRegistry(cwd=str(root), extra_roots=[str(shared)])

            result = json.loads(registry.call("read_file", {"path": str(target)}))

            self.assertEqual(result["content"], "shared context")

    def test_disallowed_tool_is_blocked_by_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            registry = ToolRegistry(cwd=str(root), disallowed_tools={"run_command"})

            result = json.loads(registry.call("run_command", {"command": "pwd"}))

            self.assertEqual(result["error"], "Tool is disabled by current policy: run_command")

    def test_allowlist_hides_unlisted_tool_definitions(self) -> None:
        registry = ToolRegistry(cwd=".", allowed_tools={"read_file"})
        tools = registry.filter_tool_definitions(
            [
                {"function": {"name": "read_file"}},
                {"function": {"name": "run_command"}},
            ]
        )

        self.assertEqual(tools, [{"function": {"name": "read_file"}}])


if __name__ == "__main__":
    unittest.main()
