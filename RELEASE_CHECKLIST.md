# Release Checklist

KaiCode is not approved for release until every item is complete.

## Preflight

- Clean git worktree.
- Version updated according to semantic versioning.
- `CHANGELOG.md` updated.
- Release notes drafted.
- `SECURITY_REVIEW.md` current.
- `DEPENDENCY_AUDIT.md` current.
- `SECURITY_AUDIT.md` current.
- `PERFORMANCE_REPORT.md` current.

## Local Verification

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e .
make PYTHON=.venv/bin/python release-check
```

Local status on 2026-06-12: passed, using Python 3.14.5 for local validation.
Remote CI status on 2026-06-12: passed on Python 3.10, 3.11, and 3.12 in
GitHub Actions run 27393424468.

## CI Verification

- GitHub Actions CI passes on Python 3.10.
- GitHub Actions CI passes on Python 3.11.
- GitHub Actions CI passes on Python 3.12.
- Multi-OS install smoke tests pass on macOS, Linux, and Windows.
- Coverage artifact uploaded.
- Dist artifacts uploaded.
- CI logs archived in GitHub Actions and indexed in `CI_VALIDATION.md`.

## Package Verification

- Wheel generated.
- Source distribution generated.
- `twine check dist/*` passes.
- Fresh virtualenv can install wheel.
- `kaicode --version` works after wheel install.
- `kaicode --help` works after wheel install.
- `pip uninstall kaicode` removes the command from the environment.

## Release

- Create signed or annotated git tag.
- Publish GitHub release notes.
- Upload verified artifacts.
- Publish to PyPI only after final approval.
