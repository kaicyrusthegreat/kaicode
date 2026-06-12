# Rollback Instructions

## PyPI Rollback

PyPI files cannot be replaced once published. If a release is bad:

1. Yank the affected version on PyPI.
2. Publish a patch release with a higher version.
3. Update GitHub release notes with the advisory.
4. Add the issue and mitigation to `CHANGELOG.md`.

## GitHub Release Rollback

1. Mark the release as pre-release or remove public release assets.
2. Keep the git tag for auditability unless it was created incorrectly before
   publication.
3. Open a patch branch from the last known-good tag.
4. Run the full release checklist again.

## User Communication

Tell users:

- Affected versions
- Whether secrets, sessions, files, or commands were exposed
- Recommended upgrade or uninstall command
- Expected fixed version
