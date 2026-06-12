# Changelog

All notable KaiCode changes should be documented in this file.

KaiCode follows semantic versioning:

- MAJOR: incompatible CLI, configuration, or provider behavior changes
- MINOR: backward-compatible features and provider/tool additions
- PATCH: backward-compatible bug fixes, docs, and security hardening

## 2.2.0 - 2026-06-12

### Added

- Goal mode for autonomous test-driven work loops.
- AI commit message generation.
- Token and estimated cost tracking.
- Release readiness documentation and production gate checklist.
- Session storage regression tests and workspace-scoped tool tests.

### Changed

- Session names are sanitized before filesystem access.
- Runtime dependencies have bounded ranges and unused dependencies were removed.
- Development dependencies are pinned in `requirements-dev.txt`.

### Security

- Session path traversal mitigation.
- Tool registry now rejects filesystem and command working directories outside
  the project workspace.

### Known Gaps

- Public release remains blocked until CI, build, audit, and multi-OS install
  checks pass on a clean release candidate.
