# Security Review

Date: 2026-06-12
Scope: KaiCode Python CLI package

## Summary

Local security checks pass on the clean virtual environment created during the
release-hardening pass. KaiCode is still not approved for public release until
the GitHub Actions workflow passes remotely and a maintainer reviews the final
release candidate.

## Reviewed Areas

### Filesystem Access

- Session names are sanitized before save/load.
- Session path construction verifies files stay in the session directory.
- Tool registry rejects file paths outside the project workspace.
- Symlink escape attempts are covered by tests.

Residual risk:

- Direct imports of low-level file tool functions bypass `ToolRegistry` scoping.
  Public agent execution should continue to use `ToolRegistry`.

### Subprocess Execution

- State-changing command execution requires user approval in the app layer.
- Dangerous command substrings are blocked in `run_command`.
- Tool registry rejects command working directories outside the project
  workspace.

Residual risk:

- `run_command` uses `shell=True`, so user-approved commands still carry shell
  expansion and command-injection risk. This is acceptable only because commands
  are displayed and approved by the user. A future hardening pass should add a
  structured argv execution path for model-generated commands.

### Environment Variables

- Provider API keys are read from environment variables or config.
- No real API keys were found by local secret regex scan.

Residual risk:

- Provider errors may include upstream response bodies. Avoid logging full
  request headers or config values.

### Temp Files And Build Artifacts

- No persistent temp-file workflow is currently used for agent actions.
- Build artifacts are ignored by git and should be generated from a clean tree.

### Arbitrary Path Writes

- Session path traversal is mitigated.
- Workspace tool paths are scoped through `ToolRegistry`.

### Stack Traces And Debug Mode

- Normal top-level CLI errors show a friendly message.
- `--debug` and `KAICODE_DEBUG=1` enable diagnostic logging/tracebacks.

## Required Before Release

- `python -m pip_audit` passes or findings are triaged. Local status: passed.
- `python -m safety check --full-report` passes or findings are triaged. Local
  status: passed.
- Fresh virtualenv build, test, and pip check pass. Local status: passed.
- CI passes on Python 3.10, 3.11, and 3.12. Remote status: pending.
- Multi-OS install smoke tests pass. Remote status: pending.
