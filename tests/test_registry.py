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


if __name__ == "__main__":
    unittest.main()
