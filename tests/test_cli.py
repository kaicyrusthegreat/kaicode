from __future__ import annotations

import unittest
from unittest.mock import patch

from click.testing import CliRunner

from kaicode.main import main


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


if __name__ == "__main__":
    unittest.main()
