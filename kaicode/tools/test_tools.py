"""Test runner — auto-detects and runs the project's test suite."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def run_tests(
    path: str = ".",
    command: str = "",
    timeout: int = 60,
) -> dict[str, Any]:
    """Run the project test suite. Auto-detects the runner if no command is given."""
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        timeout = 60

    root = Path(path).expanduser().resolve()

    if not command:
        command = _detect_test_command(root)
        if not command:
            return {
                "error": (
                    "No test suite detected. Supported: pytest, npm test, flutter test, "
                    "go test, cargo test, rspec, mvn test, gradle test. "
                    "Pass a 'command' argument to run a custom command."
                )
            }

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "command":    command,
            "returncode": result.returncode,
            "passed":     result.returncode == 0,
            "output":     output[:6000],
            "truncated":  len(output) > 6000,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Tests timed out after {timeout}s", "command": command}
    except Exception as e:
        return {"error": str(e), "command": command}


def _detect_test_command(root: Path) -> str:
    checks = [
        (["pytest.ini", "conftest.py"],                          "pytest --tb=short -q"),
        (["pyproject.toml"],                                     "pytest --tb=short -q"),
        (["setup.py", "tests"],                                  "pytest --tb=short -q"),
        (["pubspec.yaml"],                                       "flutter test"),
        (["go.mod"],                                             "go test ./..."),
        (["Cargo.toml"],                                         "cargo test"),
        (["package.json"],                                       "npm test --if-present"),
        (["Gemfile"],                                            "bundle exec rspec"),
        (["pom.xml"],                                            "mvn test -q"),
        (["build.gradle"],                                       "./gradlew test"),
        (["build.gradle.kts"],                                   "./gradlew test"),
        (["mix.exs"],                                            "mix test"),
    ]
    for markers, cmd in checks:
        if any((root / m).exists() for m in markers):
            return cmd
    return ""
