# Release Notes Draft

Version: 3.0.0
Status: Draft, release-candidate validation passed

## Highlights

- Goal mode for autonomous coding loops.
- AI-generated commit messages.
- Token and cost tracking.
- Hardened session handling and workspace-scoped tool execution.
- Local startup/session performance baseline documented.

## Release Status

Local build, package, test, and audit checks pass. GitHub Actions run
27392894480 passed on Python 3.10, 3.11, 3.12, and Linux/macOS/Windows install
smoke jobs. Public publishing is still gated on the tagged GitHub release and
maintainer confirmation of PyPI ownership/credentials.

## Known Issues

- `run_command` intentionally uses user-approved shell execution and should be
  treated as a high-trust local automation feature.
- Cloud-provider smoke tests require valid provider API keys and are not covered
  by default public CI.
