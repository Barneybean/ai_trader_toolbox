# ADR-0002: Toolkit activity log in `journal/toolkit.jsonl`

- **Status:** Accepted
- **Date:** 2026-07-11
- **Deciders:** desk owner + desk agent

## Context

The toolkit is ~20 stdlib scripts run by whatever agent is driving the desk. When a run
misbehaved — a script crashed on a connector's response shape, a chart took forever, a step
silently didn't run — there was no trail: nothing recorded what ran, with what arguments, how
long it took, or how it exited. Debugging meant re-running from memory, and reliability
("does `indicators.py` actually fail 1 run in 10?") was unmeasurable. Constraints: pure
stdlib, runtime-agnostic, and zero risk of personal data landing in a publishable file.

## Decision

We will log toolkit activity as append-only JSONL to `journal/toolkit.jsonl` via
`scripts/desk_log.py`, which offers three entry points: a `run --` wrapper that logs any
command's start/end/duration/exit code (plus a stderr tail on failure) without modifying the
wrapped script; a `log` subcommand for manual pipeline milestones; and an importable
`log_event`/`timed` API. `tail` and `stats` (per-script runs, error rate, p50/p95 duration,
unfinished runs) read it back. The file lives in git-ignored `journal/`, and every string
field is scrubbed against `scripts/pii_denylist.local.txt` before writing.

The wrapper is the primary mechanism — scripts are not individually instrumented.

## Consequences

- Failures carry evidence: argv, exit code, stderr tail, duration — and `stats` turns the
  log into a reliability dashboard per script.
- Overhead is bounded and measured (2026-07-11, `indicators.py` on 252 bars, n=10): ~62 ms
  per wrapped run — one extra interpreter startup — and ~2 JSONL lines (~420 bytes) on disk.
  Context/token cost to the driving agent is near zero by design: the wrapper adds no output
  of its own on success, `log` is silent, string fields are capped (2 KB) with stderr tails
  at 400 chars, and the log is only ever read into context via explicit `tail`/`stats`.
- Coverage depends on discipline: a script run *without* the wrapper leaves no trace, so the
  desk charter tells agents to prefer `desk_log.py run --` for engine invocations.
- The log is personal run data (tickers, timings) and must stay git-ignored; the denylist
  scrub is a backstop, not a license to log account data.

## Alternatives considered

- **Instrument every script with `logging`** — ~20 diffs now and a tax on every future
  script; the wrapper gets equivalent run-level data for free.
- **Python `logging` to text files** — unstructured lines make `stats` fragile; JSONL is
  greppable *and* parseable with zero dependencies.
- **Log inside `journal/decisions.jsonl`** — that file is the trading ledger; operational
  noise would corrupt the desk's track-record math.
