# CI Validation

Date: 2026-06-12
Release candidate: KaiCode 3.0.0
Commit: `4e2d59acdd8f722a78c9150736df232cc3e0098d`
Workflow run: [27393424468](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468)
Status: passed

[![CI](https://github.com/kaicyrusdgreat/kaicode/actions/workflows/ci.yml/badge.svg?branch=kaicode-toolcall-reliability-fixes)](https://github.com/kaicyrusdgreat/kaicode/actions/workflows/ci.yml?query=branch%3Akaicode-toolcall-reliability-fixes)

## Matrix Results

| Job | Result | Duration | Log |
|---|---|---:|---|
| Python 3.10 | passed | 57s | [job 80955667367](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468/job/80955667367) |
| Python 3.11 | passed | 46s | [job 80955667358](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468/job/80955667358) |
| Python 3.12 | passed | 58s | [job 80955667353](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468/job/80955667353) |
| Install smoke ubuntu-latest | passed | 23s | [job 80955667391](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468/job/80955667391) |
| Install smoke macos-latest | passed | 19s | [job 80955667387](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468/job/80955667387) |
| Install smoke windows-latest | passed | 59s | [job 80955667412](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27393424468/job/80955667412) |

## Validated Gates

- Formatting check passed with Ruff.
- Ruff lint passed.
- Unit tests passed with coverage artifact upload.
- Compile validation passed.
- `pip check` passed.
- Wheel and source distribution builds passed.
- `twine check dist/*` passed.
- Wheel install smoke test passed.
- `pip-audit` passed.
- `safety check --full-report` passed.
- Linux, macOS, and Windows install smoke tests passed.

## Notes

GitHub Actions emitted Node.js 20 deprecation annotations for
`actions/checkout@v4`, `actions/setup-python@v5`, and `actions/upload-artifact@v4`.
They did not fail the run. Recheck those action versions before the September
2026 Node.js 20 removal window.

The Windows install-smoke job also emitted a notice that `windows-latest`
requests are being redirected to `windows-2025-vs2026` by June 15, 2026.
