# ADR-0006: Grouped scripts with compatibility launchers

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

A flat `scripts/` directory mixed quant engines, journals, report builders, shared libraries, and
repository operations. The growing toolkit became hard to navigate, but deleting established CLI
paths would break user commands and integrations.

## Decision

Canonical implementations live under `scripts/analysis/`, `scripts/journal/`, `scripts/lib/`,
`scripts/ops/`, and `scripts/report/`. `scripts/README.md` owns the inventory. Former flat paths
remain as thin compatibility launchers and receive no independent feature development. Generated
report, cache, journal, distribution, and log directories are runtime state rather than source
structure.

## Consequences

- New tools have an obvious home and lifecycle.
- Existing commands continue working during the migration.
- Documentation and new integrations must use grouped paths so compatibility files can eventually
  be deprecated deliberately.

## Alternatives considered

- Keep the flat layout—navigation and ownership continue to degrade.
- Hard rename without launchers—needlessly breaks existing users.
