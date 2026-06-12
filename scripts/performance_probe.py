"""Measure KaiCode release-candidate performance baselines."""

from __future__ import annotations

import argparse
import json
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from kaicode.providers.base import Message
from kaicode.session import Session


def _run_command(command: list[str]) -> float:
    start = time.perf_counter()
    subprocess.run(command, check=True, capture_output=True, text=True)
    return time.perf_counter() - start


def _max_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return rss / (1024 * 1024)
    return rss / 1024


def _session_roundtrip(message_count: int) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as tmp:
        sessions_dir = Path(tmp) / "sessions"
        session = Session(
            name="",
            provider="ollama",
            model="qwen3:8b",
            cwd=tmp,
            messages=[
                Message(role="user" if i % 2 == 0 else "assistant", content=f"message {i}")
                for i in range(message_count)
            ],
        )
        with patch("kaicode.session.SESSIONS_DIR", sessions_dir):
            start = time.perf_counter()
            saved = session.save(f"perf-{message_count}")
            save_seconds = time.perf_counter() - start

            start = time.perf_counter()
            loaded = Session.load(f"perf-{message_count}")
            load_seconds = time.perf_counter() - start

        return {
            "messages": float(len(loaded.messages)),
            "bytes": float(saved.stat().st_size),
            "save_ms": save_seconds * 1000,
            "load_ms": load_seconds * 1000,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kaicode", default="kaicode", help="Path to the kaicode executable")
    parser.add_argument("--warm-runs", type=int, default=5)
    args = parser.parse_args()

    command = [args.kaicode, "--version"]
    cold = _run_command(command)
    warm = [_run_command(command) for _ in range(args.warm_runs)]
    small_session = _session_roundtrip(10)
    large_session = _session_roundtrip(5000)

    result = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "command": command,
        "cold_start_ms": cold * 1000,
        "warm_start_ms_median": statistics.median(warm) * 1000,
        "warm_start_ms_min": min(warm) * 1000,
        "warm_start_ms_max": max(warm) * 1000,
        "small_session": small_session,
        "large_session": large_session,
        "max_rss_mb": _max_rss_mb(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
