# Dependency Audit

Date: 2026-06-12
Status: Local audit passed

## Runtime Dependency Review

Removed as unused:

- `gitpython`
- `pathspec`
- `beautifulsoup4`

Retained:

- `rich`: terminal rendering
- `httpx`: provider and web HTTP clients
- `pyyaml`: config loading
- `click`: CLI entrypoint
- `openai`: OpenAI provider
- `openai`: OpenAI provider
- `groq`: Groq provider
- `prompt_toolkit`: interactive REPL
- `pygments`: terminal syntax highlighting
- `pyautogui`: explicit GUI automation tools

## Required Commands

```bash
python -m pip check
python -m pip_audit
python -m safety check --full-report
```

## Findings

- `python -m pip check`: passed with no broken requirements.
- `python -m pip_audit`: passed with no known vulnerabilities found.
- `python -m safety check --full-report`: passed with 0 vulnerabilities
  reported.

Notes:

- `pip-audit` skipped `kaicode` and optional `cyrusago` because they are local or
  not published on PyPI in this environment.
- Initial audit findings in dev tooling were remediated by updating `wheel`,
  `pytest`, and `safety`.
