# ADR-0004: Structured runtime activity logs

- **Status:** Accepted
- **Date:** 2026-07-12
- **Supersedes:** ADR-0002

## Context

The original activity logger relied mainly on an optional command wrapper and wrote to
`journal/toolkit.jsonl`. Headless bridge, scheduled, report, and journal entrypoints need one
observable runtime timeline, while journals and operational logs have different privacy and
lifecycle rules.

## Decision

Shared logging lives in `scripts/lib/desk_log.py`. User-facing Python entrypoints invoke
`desk_log.run(main)` and may also emit structured events. Human-readable output goes to
`logs/desk.log`; machine-readable events go to `logs/activity.jsonl`; the bridge keeps its local
events under `chat-bot-bridge/logs/`. All log directories are git-ignored runtime state. The
`desk_log.py run --` compatibility wrapper remains available for external commands.

## Consequences

- Normal entrypoints leave evidence without relying on agent memory or an optional wrapper.
- Operational data no longer shares a storage contract with trading journals.
- Logs may contain private run context and must never be copied into the public toolkit.

## Alternatives considered

- Keep wrapper-only logging—coverage depends too heavily on caller discipline.
- Store events in the journal—mixes operational telemetry with decision memory.
