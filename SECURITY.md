# Security Policy

## Supported Versions

Only the latest released KaiCode version receives security fixes.

## Reporting A Vulnerability

Report vulnerabilities privately by contacting Kai Cyrus at `me@kaicyrus.com`.
Do not open a public issue for suspected secrets exposure, path traversal,
command execution, arbitrary file access, or provider-token leakage.

Include:

- KaiCode version
- Operating system and Python version
- Steps to reproduce
- Expected impact
- Whether a secret, token, session file, or local path was exposed

## Security Expectations

- API keys belong in environment variables or user config, never in git.
- KaiCode should not print stack traces during normal CLI usage.
- User-approved tool execution must remain explicit and visible.
- Filesystem tools should stay scoped to the current project workspace.
