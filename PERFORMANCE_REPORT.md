# Performance Report

Date: 2026-06-12
Release candidate: KaiCode 3.0.0

## Environment

- OS: macOS Darwin
- Python: 3.14.5
- Command measured: `.venv/bin/kaicode --version`
- Probe: `scripts/performance_probe.py`

These numbers are a local baseline for regression tracking. Supported release
versions still need remote validation on Python 3.10, 3.11, and 3.12.

## Startup

| Metric | Result |
|---|---:|
| Cold startup | 353.75 ms |
| Warm startup median | 245.80 ms |
| Warm startup min | 230.53 ms |
| Warm startup max | 261.64 ms |

Cold startup is the first measured process invocation in the probe. Warm startup
is the median of five subsequent invocations.

## Session Save And Load

| Session Size | JSON Size | Save | Load |
|---:|---:|---:|---:|
| 10 messages | 918 bytes | 0.42 ms | 0.16 ms |
| 5,000 messages | 346,643 bytes | 2.91 ms | 4.70 ms |

## Memory

| Metric | Result |
|---|---:|
| Probe max RSS | 49.11 MB |

The memory number is measured from the probe process after importing KaiCode
session primitives and performing session roundtrips. It is not an interactive
REPL long-session memory profile.

## Baseline Assessment

- CLI version-command warm startup is below 300 ms locally.
- Session serialization is fast for small and large JSON session files.
- No memory growth test for a full interactive provider session was performed.

## Follow-Up Benchmarks

Before public production release, capture:

- Startup measurements on Python 3.10, 3.11, and 3.12.
- Linux and Windows startup/session measurements.
- Interactive REPL memory usage over a long session.
- Provider-streaming latency with Ollama and at least one cloud provider.
