# ADR-0007: Significant-change smoke gate with human review

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

Consistency and privacy checks do not prove that changed entrypoints still start, import, and
exercise representative behavior. A full desk run is too expensive for every push.

## Decision

`scripts/ops/smoke_test.py` classifies significant changed paths and runs targeted local checks for
Python, analysis, journal, reports, operations, bridge syntax/routing, documentation integrity, and
privacy wiring. The pre-push hook derives real pushed revision ranges. When a suite runs, the push
stops for human review and proceeds only after the reviewer retries with `SMOKE_REVIEW_OK=1`.

## Consequences

- Meaningful updates get proportional behavior checks automatically.
- Human review is explicit and cannot be silently treated as a passing test.
- New subsystems must extend the classifier and representative smoke behavior.

## Alternatives considered

- Syntax checks only—miss behavior and wiring regressions.
- Full end-to-end runs—too slow and capability-dependent for each push.
