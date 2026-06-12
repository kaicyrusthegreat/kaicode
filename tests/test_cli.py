from __future__ import annotations

import unittest
from unittest.mock import patch

from click.testing import CliRunner

from kaicode.main import _build_tool_policy, main


class CliTests(unittest.TestCase):
    def test_version_command(self) -> None:
        result = CliRunner().invoke(main, ["--version"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("kaicode, version 3.0.0", result.output)

    def test_invalid_config_does_not_print_traceback(self) -> None:
        runner = CliRunner()
        with (
            patch("kaicode.main.create_default_config"),
            patch("kaicode.main.KaiConfig.load", side_effect=ValueError("Invalid global config")),
        ):
            result = runner.invoke(main, [])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("Invalid global config", result.output)
        self.assertNotIn("Traceback", result.output)

    def test_output_format_requires_print_mode(self) -> None:
        result = CliRunner().invoke(main, ["--output-format", "json"])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("--output-format requires --print", result.output)

    def test_tool_policy_accepts_claude_style_aliases(self) -> None:
        allowed, denied = _build_tool_policy(
            ("Bash(git status) Read,Edit",),
            (),
            ("Write",),
        )

        self.assertEqual(allowed, {"run_command", "read_file", "edit_file"})
        self.assertEqual(denied, {"create_file"})

    def test_safe_mode_allows_only_read_only_tools(self) -> None:
        allowed, denied = _build_tool_policy((), (), (), safe_mode=True)

        self.assertIsNotNone(allowed)
        self.assertIn("read_file", allowed or set())
        self.assertIn("git_diff", allowed or set())
        self.assertNotIn("run_command", allowed or set())
        self.assertEqual(denied, set())


if __name__ == "__main__":
    unittest.main()
