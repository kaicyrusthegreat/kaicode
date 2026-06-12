# KaiCode Release Readiness

Date: 2026-06-12
Project type: Python CLI package

This file tracks the production-readiness checklist for the current KaiCode
repository. Mobile store items such as APK, AAB, IPA, provisioning profiles,
notched devices, and in-app purchases are not applicable unless a separate
mobile app repository is added.

## Current Gate Status

Release status: Release candidate remotely validated, not yet approved for
public release.

Local verification completed:

- Python syntax compilation passed with `python3 -m compileall kaicode`.
- Secret scan found no obvious real committed API keys. README examples are
  placeholders.
- A focused session-storage safety test suite was added.
- Expanded tests now cover config parse errors, corrupted session files,
  extremely long Unicode session names, CLI error presentation, tool workspace
  scoping, symlink escape attempts, command guard behavior, and checkpoint
  undo/redo.
- CI workflow, pinned dev requirements, Makefile, release script, changelog,
  security policy, contributing guide, code of conduct, security review,
  dependency audit template, security audit template, release checklist,
  release notes draft, and rollback instructions have been added.

Blocking items:

- No crash reporting or analytics exists for a packaged CLI release. This is
  consistent with the README's no-telemetry positioning, but operational
  monitoring for releases still needs a maintainer process.
- Tagged Git release and release notes publication have not been performed.
- PyPI project ownership, credentials, maintainer list, and Trusted Publishing
  configuration still require maintainer confirmation before upload.

Local release validation passed:

- Clean venv created.
- Pinned dev dependencies installed from `requirements-dev.txt`.
- `python -m pytest` passed: 15 tests, coverage XML generated, 14.54% current
  baseline coverage.
- `python -m compileall kaicode tests` passed.
- `python -m ruff format --check .` passed.
- `python -m ruff check .` passed.
- `python -m pip check` passed.
- `python -m build` generated wheel and source distribution.
- `python -m twine check dist/*` passed.
- `python -m pip_audit` passed with no known vulnerabilities found.
- `python -m safety check --full-report` passed with 0 vulnerabilities.
- Fresh wheel install smoke test passed in `/private/tmp/kaicode-wheel-smoke-20260612`.
- Installed CLI smoke test passed: `kaicode --version`.
- Local performance baseline captured in `PERFORMANCE_REPORT.md`.
- GitHub Actions run 27393424468 passed on Python 3.10, 3.11, and 3.12.
- GitHub Actions install smoke passed on Linux, macOS, and Windows.

## Required Release Commands

Run from a clean checkout:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pip install -r requirements-dev.txt
python3 -m compileall kaicode
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
python3 -m pip check
python3 -m pip_audit
python3 -m safety check --full-report
```

If the CyruSagO provider should be officially supported in a release, install
and verify the optional extra:

```bash
python3 -m pip install -e ".[cyrusago,dev]"
kaicode --provider cyrusago --version
```

## Checklist Mapping

### Core Stability

- CLI launch must be tested repeatedly across supported Python versions.
- Offline mode must be tested for local Ollama and for cloud-provider failures.
- Provider failures must show user-facing fallback errors without tracebacks.
- Long-running sessions must be checked for memory growth.

### UI/UX Polish

- Terminal rendering must be checked in standard light and dark terminal themes.
- Prompt toolbar and Rich panels must be checked on narrow terminal widths.
- Placeholder or experimental text must be removed from release docs.

### Authentication, Security, And Privacy

- No user account authentication exists in this CLI package.
- Cloud API keys must remain environment/config only; never commit real keys.
- Session filenames are sanitized before save/load.
- Shell execution remains user-approved and dangerous patterns are blocked, but
  this should receive a dedicated security review before release.
- Add or link privacy policy and terms before broad public distribution.

### Backend And API Validation

- Cloud provider integrations require live smoke tests with valid API keys.
- Ollama and OpenAI-compatible providers require local endpoint smoke tests.
- Network timeouts and retry behavior should be tested under poor connectivity.

### Store Readiness

- Mobile app store sections are not applicable to this repository.
- For Python distribution, prepare and verify PyPI artifacts instead.

### Analytics And Monitoring

- No telemetry is present, which matches the README's local-first/no-telemetry
  positioning.
- If crash reporting or analytics are added later, update the privacy policy.

### Codebase Cleanup

- Remove unused dependencies before release.
- Packaging metadata is now centralized in `pyproject.toml`; legacy
  `setup.cfg` was removed.
- Continue consolidating duplicated version declarations.

### Testing

- Add unit tests for provider message conversion, tool parsing, command guards,
  config loading, and checkpoint undo/redo.
- Add integration tests for the CLI entrypoint and provider fallback behavior.
- Add smoke tests for `kaicode --version`, one-shot mode, and goal mode.

### Release Infrastructure

- CI now targets Python 3.10, 3.11, and 3.12.
- CI runs compile, format check, lint, tests with coverage, pip check, build,
  twine package checks, wheel install smoke test, and vulnerability scans.
- Multi-OS install smoke tests passed for macOS, Linux, and Windows.
- Rollback process is documented in `ROLLBACK.md`.

### Final Verification

- Build from a fresh clone only.
- Verify no staging endpoints, mock data, or test-only files are packaged.
- Verify package size and import time.
- Verify README install and quick-start commands exactly.

## Required Final Deliverables

For this Python CLI package, release deliverables are:

- Source distribution and wheel in `dist/`: present locally.
- Full changelog: present.
- Test report: local pytest output and `coverage.xml` generated.
- Performance and startup report: present.
- Security review summary: present.
- Environment variable documentation: present in README.
- Deployment or PyPI publishing documentation: present in `PUBLISHING.md`; PyPI
  ownership and credentials still need maintainer confirmation.
- Rollback/yank instructions: present.
- Known issues list: present in release notes draft.
