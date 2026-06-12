PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python

.PHONY: venv install-dev lint format-check test coverage compile build check audit release-check clean

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip

install-dev: venv
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt
	$(VENV_PYTHON) -m pip install -e .

lint:
	$(PYTHON) -m ruff check .

format-check:
	$(PYTHON) -m ruff format --check .

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=kaicode --cov-report=term-missing --cov-report=xml

compile:
	$(PYTHON) -m compileall kaicode tests

build:
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

check:
	$(PYTHON) -m pip check

audit:
	$(PYTHON) -m pip_audit
	$(PYTHON) -m safety check --full-report

release-check: compile format-check lint coverage check build audit

clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('build', 'dist', 'htmlcov', '.pytest_cache', '.ruff_cache')]"
