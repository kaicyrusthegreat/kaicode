# Release Notes Draft

Version: 2.2.0
Status: Draft, not approved

## Highlights

- Goal mode for autonomous coding loops.
- AI-generated commit messages.
- Token and cost tracking.
- Hardened session handling and workspace-scoped tool execution.
- Local startup/session performance baseline documented.

## Release Status

Local build, package, test, and audit checks pass. This release is still blocked
until GitHub Actions CI passes on supported Python versions and multi-OS install
smoke tests complete.

## Known Issues

- `run_command` intentionally uses user-approved shell execution and should be
  treated as a high-trust local automation feature.
- Cloud-provider smoke tests require valid provider API keys and are not covered
  by default public CI.
