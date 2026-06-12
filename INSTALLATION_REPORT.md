# Installation Report

Date: 2026-06-12
Release candidate: KaiCode 2.2.0

## Local macOS Wheel Install

Environment:

- OS: macOS Darwin
- Python: 3.14.5
- Wheel: `dist/kaicode-2.2.0-py3-none-any.whl`
- Smoke venv: `/private/tmp/kaicode-wheel-smoke-20260612`

Results:

- Wheel installation: passed.
- `kaicode --version`: passed, reported `kaicode, version 2.2.0`.
- `kaicode --help`: passed, expected CLI options were present.
- Config load smoke test: passed using a temporary project `.kaicode` file.
- Session save/load smoke test: passed using an isolated temporary session directory.
- `python -m pip check`: passed with no broken requirements.
- Uninstall cleanup: passed, `kaicode` command was removed from the smoke venv.

## GitHub Actions Cross-Platform Install

Validated in GitHub Actions run
[27392894480](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480):

- Linux: passed on `ubuntu-latest`.
- macOS: passed on `macos-latest`.
- Windows: passed on `windows-latest`.

Expected validation on each OS:

- Fresh package install succeeds.
- `kaicode --version` succeeds.
- `kaicode --help` succeeds.
- Config loading succeeds.
- Session save/load succeeds.
- Dependency resolution is clean.
- Uninstall removes the `kaicode` command.
- CI artifact logs are retained in GitHub Actions.

## Manual Follow-Up

CI logs are linked from `CI_VALIDATION.md`. Separate physical-machine
verification can still be performed for extra confidence before a broad public
announcement.
