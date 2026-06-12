# Security Audit Report

Date: 2026-06-12
Status: Local audit passed

## Required Tooling

- `pip-audit`
- `safety`

## Commands

```bash
python -m pip_audit
python -m safety check --full-report
```

## Results

- `python -m pip_audit`: no known vulnerabilities found.
- `python -m safety check --full-report`: 0 vulnerabilities reported.

Limitations:

- `pip-audit` could not audit local/non-PyPI packages `kaicode` and `cyrusago`.
- GitHub Actions run 27393424468 ran `pip-audit` and Safety successfully on
  Ubuntu for Python 3.10, 3.11, and 3.12. macOS and Windows jobs cover install
  smoke validation only.
