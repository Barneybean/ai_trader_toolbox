# ADR-0001: Record key decisions as ADRs

- **Status:** Accepted
- **Date:** 2026-07-11
- **Deciders:** desk owner + desk agent

## Context

This repo is one source of truth read by several agent runtimes, and it iterates fast: gates
get added (sufficiency gate after the MRVL 2026-07-09 miss), scripts get reshaped, privacy
rules tighten. The *why* behind those changes lived only in chat transcripts and commit
messages — invisible to a future run (or contributor) that's about to propose the same
rejected alternative or quietly weaken a deliberate constraint. Reports and the decision
journal capture trading calls; nothing captured **build** decisions.

## Decision

We will record key decisions as Architecture Decision Records in `docs/adr/`, numbered
`NNNN-slug.md`, scaffolded by `scripts/new_adr.py` from `docs/adr/template.md`. Scope: desk
method, toolkit architecture, data contracts, privacy posture, runtime/broker support.
ADRs are immutable once accepted — course changes get a new ADR that supersedes the old one.
The process itself is documented in `docs/adr/README.md`.

## Consequences

- Method and architecture changes carry their rationale with them; agents can be pointed at
  `docs/adr/` before proposing structural changes.
- Small ongoing writing cost per significant change; the "when to write one" test in the
  README keeps routine fixes exempt.
- ADRs are public: they must describe mechanisms, never personal data — the PII gate applies
  to this directory like everywhere else.

## Alternatives considered

- **Keep rationale in commit messages** — not discoverable by agents at run time, and long
  rationale doesn't survive squash merges.
- **A single DECISIONS.md** — merge-conflict magnet, no lifecycle (proposed/superseded), and
  it tempts in-place rewrites that erase history.
- **Reuse `journal/decisions.jsonl`** — that ledger is for trading calls with outcomes and
  alpha math; mixing build decisions in would pollute the desk's calibration stats.
