from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kaicode.checkpoint import CheckpointStack
from kaicode.tools.file_tools import run_command
from kaicode.tools.test_tools import _detect_test_command


class ToolTests(unittest.TestCase):
    def test_dangerous_shell_pattern_is_blocked(self) -> None:
        result = run_command("rm -rf /")

        self.assertIn("Blocked dangerous command pattern", result["error"])

    def test_pytest_detection_from_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

            command = _detect_test_command(root)

        self.assertIn("-m pytest", command)

    def test_checkpoint_undo_redo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.txt"
            stack = CheckpointStack()
            before = None
            target.write_text("after", encoding="utf-8")
            after = "after"

            stack.record(str(target), before, after, "create_file")
            stack.undo()
            self.assertFalse(target.exists())

            stack.redo()
            self.assertEqual(target.read_text(encoding="utf-8"), "after")


if __name__ == "__main__":
    unittest.main()
