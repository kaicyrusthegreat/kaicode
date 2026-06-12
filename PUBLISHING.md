# Publishing Process

KaiCode 2.2.0 is approved for release-candidate validation, not public
production release, until the final checklist is signed off.

## Ownership Prerequisites

Before publishing, the maintainer must confirm:

- PyPI project ownership for `kaicode`.
- PyPI account recovery methods are current.
- Maintainer list is accurate.
- Trusted Publishing is configured for this GitHub repository, or a scoped PyPI
  API token is stored securely outside the repository.
- GitHub release permissions are limited to trusted maintainers.

## Build

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
make PYTHON=.venv/bin/python release-check
```

Expected artifacts:

- `dist/kaicode-2.2.0-py3-none-any.whl`
- `dist/kaicode-2.2.0.tar.gz`
- `coverage.xml`

## Tagging

Use an annotated tag. Use a signed tag when a configured signing key is
available.

```bash
git tag -a v2.2.0 -m "Release KaiCode 2.2.0"
git push origin v2.2.0
```

## GitHub Release

1. Open the release page for `v2.2.0`.
2. Paste the contents of `RELEASE_NOTES.md`.
3. Attach the wheel and source distribution from `dist/`.
4. Mark the release as latest only after CI and install validation pass.

## PyPI Publishing

Preferred path: GitHub Trusted Publishing from a protected release workflow.

Manual fallback:

```bash
.venv/bin/python -m twine upload dist/*
```

Do not publish to PyPI until:

- GitHub Actions is green.
- macOS, Linux, and Windows install smoke tests are green.
- `SECURITY_REVIEW.md`, `DEPENDENCY_AUDIT.md`, and `SECURITY_AUDIT.md` are
  current.
- `RELEASE_CHECKLIST.md` is signed off by the maintainer.

## Recovery

If a bad artifact is published, follow `ROLLBACK.md`. PyPI files cannot be
replaced; publish a higher patch version after yanking the affected release.
