from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kaicode.config import KaiConfig


class ConfigTests(unittest.TestCase):
    def test_invalid_global_yaml_gets_friendly_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.yaml"
            config_file.write_text("providers: [unterminated\n", encoding="utf-8")

            with patch("kaicode.config.GLOBAL_CONFIG_FILE", config_file):
                with self.assertRaisesRegex(ValueError, "Invalid global config"):
                    KaiConfig()._load_global()

    def test_non_mapping_config_gets_friendly_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.yaml"
            config_file.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

            with patch("kaicode.config.GLOBAL_CONFIG_FILE", config_file):
                with self.assertRaisesRegex(ValueError, "expected a YAML mapping"):
                    KaiConfig()._load_global()


if __name__ == "__main__":
    unittest.main()
