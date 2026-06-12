# CI Validation

Date: 2026-06-12
Release candidate: KaiCode 2.2.0
Commit: `448c805ed75f82be051a21a78d438f1ada61ea82`
Workflow run: [27392894480](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480)
Status: passed

[![CI](https://github.com/kaicyrusdgreat/kaicode/actions/workflows/ci.yml/badge.svg?branch=kaicode-toolcall-reliability-fixes)](https://github.com/kaicyrusdgreat/kaicode/actions/workflows/ci.yml?query=branch%3Akaicode-toolcall-reliability-fixes)

## Matrix Results

| Job | Result | Duration | Log |
|---|---|---:|---|
| Python 3.10 | passed | 58s | [job 80954091558](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480/job/80954091558) |
| Python 3.11 | passed | 55s | [job 80954091631](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480/job/80954091631) |
| Python 3.12 | passed | 1m19s | [job 80954091583](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480/job/80954091583) |
| Install smoke ubuntu-latest | passed | 27s | [job 80954091550](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480/job/80954091550) |
| Install smoke macos-latest | passed | 32s | [job 80954091556](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480/job/80954091556) |
| Install smoke windows-latest | passed | 2m7s | [job 80954091543](https://github.com/kaicyrusdgreat/kaicode/actions/runs/27392894480/job/80954091543) |

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
