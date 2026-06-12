#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

"$PYTHON" -m pip install -r requirements-dev.txt
"$PYTHON" -m pip install -e .
"$PYTHON" -m compileall kaicode tests
"$PYTHON" -m ruff format --check .
"$PYTHON" -m ruff check .
"$PYTHON" -m pytest
"$PYTHON" -m pip check
"$PYTHON" -m build
"$PYTHON" -m twine check dist/*
"$PYTHON" -m pip_audit
"$PYTHON" -m safety check --full-report
