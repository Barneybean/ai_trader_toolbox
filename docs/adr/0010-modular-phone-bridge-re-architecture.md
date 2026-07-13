# ADR-0010: Modular phone-bridge re-architecture

- **Status:** Accepted
- **Date:** 2026-07-12
- **Deciders:** desk maintainer, review

## Context

The bridge began as a single `server.js` that grew to carry provider transport, session
management, agent routing, run control, order-ticket handling, and reporting. As phone-driven
capabilities accumulated, the monolith became hard to test in isolation and hard to reason about
for security review — exactly the surface where prompt-injection and execution-authority mistakes
are most costly. Behavior that should be unit-testable (availability fallback, ticket resolution,
output redaction) was entangled with I/O.

## Decision

Extract the bridge's decision logic into small, side-effect-free modules, each with a Node
`--test` suite, and keep `server.js` as the transport/orchestration shell that composes them:

- `agent-routing` — availability/fallback classification, broker-intent detection, run circuit breaker.
- `model-routing` — interleaved model selection across agents for scheduled and phone runs.
- `availability-recovery` — reset-aware retry scheduling when a model is rate-limited.
- `ticket-approval` — durable resolution of natural-language approvals ("ok to execute") to the exact saved numbered tickets.
- `remote-control` — phone run commands (`/run`, `/stop`, `/steer`, `/decide`, `/agent`).
- `change-review` — private, redacted mobile code-change review artifacts for repo edits made during a phone turn.
- `phone-output` — plain-text formatting + credential/account redaction for outbound messages.
- `run-telemetry` — compact live run cards from structured agent events.
- `inbound-media` — provider-neutral inbound image attachments.
- `broker-preflight` — report broker-capability probe wiring.
- `scheduled-task` — scheduled-run mode/prompt assembly.

Order discipline, account privacy, and mode gating are unchanged: the public-safe default remains
`manual`, only the locally configured execution account is tradable, and money movement is
forbidden in every mode. `smoke_test.py` gains a `node --test` suite over the bridge modules and an
updated import assertion matching the narrowed availability-error contract (a failed tool command is
no longer misclassified as an agent-availability failure).

## Consequences

- Each capability is unit-tested and independently reviewable; the security-sensitive paths
  (redaction, authorization resolution, fallback) have explicit regression coverage.
- `server.js` shrinks to composition; new providers/capabilities slot in without touching unrelated logic.
- New obligation: the module boundaries and their tests must be kept in sync, and the smoke gate now
  runs the bridge behavior suite whenever `chat-bot-bridge/` changes.
- Fork users adopting the update must re-resolve `YOUR_NAME` plist placeholders as before; no
  personal paths, labels, tokens, or accounts are introduced by the modules (secrets stay in `.env`).

## Alternatives considered

- **Keep the monolith, add features inline.** Rejected — the untestable-surface problem compounds,
  and security review of a 2k-line file is unreliable.
- **A dependency/framework (Express, a bot SDK).** Rejected — the zero-npm-dependency invariant is a
  deliberate supply-chain and portability choice; Node built-ins suffice.
