# Contributing

Thanks for helping make KaiCode sturdier.

## Development Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e .
```

## Required Checks

Run these before opening a pull request:

```bash
.venv/bin/python -m compileall kaicode tests
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest
.venv/bin/python -m pip check
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

Or run:

```bash
make PYTHON=.venv/bin/python release-check
```

## Pull Requests

- Keep changes focused.
- Add tests for behavior changes.
- Update `CHANGELOG.md` for user-facing changes.
- Update `SECURITY_REVIEW.md` for security-sensitive changes.
- Never commit secrets, real API keys, local sessions, or build artifacts.
