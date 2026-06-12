"""Installed-package smoke checks for CI and manual release validation."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from kaicode.config import KaiConfig
from kaicode.providers.base import Message
from kaicode.session import Session


def _run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kaicode", default="kaicode")
    args = parser.parse_args()

    version = _run([args.kaicode, "--version"])
    if "kaicode, version" not in version:
        raise AssertionError(version)

    help_text = _run([args.kaicode, "--help"])
    if "--provider" not in help_text or "--debug" not in help_text:
        raise AssertionError("CLI help is missing expected options")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project_config = root / ".kaicode"
        project_config.write_text(
            "default_provider: ollama\nsystem_prompt: smoke test\n", encoding="utf-8"
        )
        with patch("pathlib.Path.cwd", return_value=root):
            config = KaiConfig()
            config._load_project()
        if config.default_provider != "ollama" or config.system_prompt != "smoke test":
            raise AssertionError("Project config did not load as expected")

        sessions_dir = root / "sessions"
        session = Session(
            name="",
            provider="ollama",
            model="qwen3:8b",
            cwd=str(root),
            messages=[Message(role="user", content="hello")],
        )
        with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
            session.save("install/smoke")
            loaded = Session.load("install/smoke")
        if loaded.messages[0].content != "hello":
            raise AssertionError("Session save/load failed")

    print("install smoke passed")


if __name__ == "__main__":
    main()
