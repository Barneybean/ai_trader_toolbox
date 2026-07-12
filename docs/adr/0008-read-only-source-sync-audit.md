# ADR-0008: Read-only source sync audit before public ports

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

Repeated private-to-public updates exposed failure modes that ordinary PII scans cannot catch:
parallel directories, copied machine defaults, stale paths and manuals, deleted public-only assets,
shared remotes, contradictory execution policy, and generic capabilities omitted because they were
mixed with private state.

## Decision

Every port from another desk, branch, fork, or source begins with the read-only
`scripts/ops/sync_audit.py`. Its versioned policy classifies paths as never-import,
preserve-public, sanitize-required, reusable-candidate, or manual-review. It checks repository and
remote isolation, canonical paths, required public invariants, secret templates, sensitive content,
and local denylist terms. It produces a review inventory but never copies, edits, stages, commits,
or pushes.

Porting remains a manual capability-unit workflow followed by consistency, privacy, behavior,
smoke, and human-review gates. Shared-repository worktrees require explicit acknowledgement;
sharing the public remote remains an error.

## Consequences

- Classification and safety rules are reproducible instead of living in chat history.
- Private state is expected and reported as blocked-by-design rather than treated as a sync miss.
- Public-only files and compatibility surfaces become first-class preservation requirements.
- The policy and auditor require maintenance when new state categories or subsystems appear.

## Alternatives considered

- Automatic mirroring with exclusions—one missed exclusion permanently publishes private data.
- A prose checklist only—cannot detect remotes, aliases, populated secrets, or drift mechanically.
- PII scanning alone—does not catch unsafe policy defaults or structural conflicts.
