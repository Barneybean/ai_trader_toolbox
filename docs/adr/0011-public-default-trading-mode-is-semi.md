# ADR-0011: Public default trading mode is `semi`

- **Status:** Accepted
- **Date:** 2026-07-13
- **Deciders:** repo owner, review
- **Supersedes:** the incidental "public default remains `manual`" statement in ADR-0010

## Context

The toolkit shipped with `manual` as the public default execution mode — the most conservative
setting, requiring a restate/preview/confirm round-trip on every single order. `semi` (reports
propose numbered, fully-specified tickets; the user replies "approve N" and exactly those execute)
was available but opt-in. In practice the desk is operated in `semi`, and the extra per-order
friction of `manual` added no safety over `semi` for the common case: **neither mode ever executes
without an explicit user approval**. `semi` still gates every order behind a numbered ticket the
user must approve; it only replaces per-order restate/confirm with batch approval of pre-specified
tickets. The mode default was pinned in code and enforced as a sync-policy invariant, so changing
it is a deliberate, checkable posture change rather than a one-line flip.

## Decision

Make `semi` the public default execution mode. Concretely:

- `scripts/ops/desk_mode.py` `DEFAULT = "semi"`; `chat-bot-bridge/chat-rules.js` `currentMode()`
  falls back to `'semi'`; `skills/decision/trading-modes.md` states the missing/unreadable-file
  default is `semi`.
- `docs/source-sync-policy.json` `required_text` now enforces the `semi` default in those three
  files (the invariant tracks the new posture, so a careless sync cannot silently revert it).
- Docs updated to describe `semi` as the default and `manual` as the per-order kill switch:
  `SKILL.md`, `PORTABILITY.md`, `docs/open-source-boundary.md`, `skills/README.md`,
  `skills/execution/data-and-execution.md`, `chat-bot-bridge/README.md`.

Unchanged: `manual` remains the advise-only kill switch (`/mode manual`); `full` remains
experimental and explicit-opt-in only; only the locally configured execution account is tradable in
any mode; money movement is forbidden in every mode.

## Consequences

- A fresh clone's scheduled/phone runs propose numbered tickets by default instead of requiring a
  per-order confirm dialog — a smoother default for the intended single-operator use.
- Still no execution without explicit approval, so the change does not introduce autonomous trading;
  the meaningful safety boundary (broker auth + `full` opt-in) is untouched. A fork with no broker
  connector cannot trade regardless of default mode.
- Failure mode introduced: a user who approves numbered tickets casually has a shorter path to a
  fill than under `manual`. `/mode manual` remains the one-word kill switch, and the sufficiency/risk
  gates and account-scope limits are unchanged.
- New obligation: the `semi` default is now the invariant; a future change back to `manual` (or to
  `full`) must update both the pinned files and `source-sync-policy.json` together.

## Alternatives considered

- **Keep `manual` as the public default.** Rejected by the repo owner — it adds per-order friction
  without added safety over `semi` for the intended operator, and diverges from how the desk runs.
- **Default to `full`.** Rejected — autonomous execution must never be a default; it stays
  experimental, explicit-opt-in, and bounded by every playbook gate.
