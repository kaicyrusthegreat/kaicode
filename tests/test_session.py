from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kaicode.providers.base import Message
from kaicode.session import Session


class SessionStorageTests(unittest.TestCase):
    def test_save_sanitizes_path_separators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            session = Session(
                name="",
                provider="ollama",
                model="qwen3:8b",
                cwd=tmp,
                messages=[Message(role="user", content="hello")],
            )

            with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
                saved_path = session.save("../outside/session")

            self.assertEqual(saved_path.parent, sessions_dir.resolve())
            self.assertEqual(saved_path.name, ".._outside_session.json")
            self.assertEqual(session.name, ".._outside_session")
            self.assertFalse((Path(tmp) / "outside").exists())

    def test_load_uses_the_same_safe_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            session = Session(
                name="",
                provider="ollama",
                model="qwen3:8b",
                cwd=tmp,
                messages=[Message(role="assistant", content="saved")],
            )

            with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
                session.save("release/session")
                loaded = Session.load("release/session")

            self.assertEqual(loaded.name, "release_session")
            self.assertEqual(loaded.messages[0].content, "saved")

    def test_save_truncates_extremely_long_unicode_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            session = Session(name="", provider="ollama", model="qwen3:8b", cwd=tmp)
            long_name = "release-" + ("å" * 200)

            with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
                saved_path = session.save(long_name)

            self.assertEqual(len(session.name), 120)
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.stem, session.name)

    def test_load_corrupted_session_reports_friendly_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            sessions_dir.mkdir()
            (sessions_dir / "bad.json").write_text("{", encoding="utf-8")

            with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
                with self.assertRaisesRegex(ValueError, "corrupted"):
                    Session.load("bad")

    def test_list_sessions_ignores_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            sessions_dir.mkdir()
            (sessions_dir / "broken.json").write_text("{", encoding="utf-8")
            (sessions_dir / "ok.json").write_text(
                json.dumps(
                    {
                        "name": "ok",
                        "provider": "ollama",
                        "model": "qwen3:8b",
                        "messages": [],
                        "updated_at": 1,
                    }
                ),
                encoding="utf-8",
            )

            with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
                sessions = Session.list_sessions()

            self.assertEqual([s["name"] for s in sessions], ["ok"])

    def test_latest_can_be_scoped_to_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sessions_dir = Path(tmp) / "sessions"
            cwd_a = Path(tmp) / "a"
            cwd_b = Path(tmp) / "b"
            cwd_a.mkdir()
            cwd_b.mkdir()
            older = Session(name="", provider="ollama", model="qwen3:8b", cwd=str(cwd_a))
            newer = Session(name="", provider="ollama", model="qwen3:8b", cwd=str(cwd_b))

            with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
                older.save("older")
                time.sleep(0.01)
                newer.save("newer")
                latest_for_a = Session.latest(str(cwd_a))
                latest_any = Session.latest()

            self.assertEqual(latest_for_a, "older")
            self.assertEqual(latest_any, "newer")


if __name__ == "__main__":
    unittest.main()
