# ADR-0012: Manual phone agent picker is independent of availability fallback

- **Status:** Accepted
- **Date:** 2026-07-13
- **Deciders:** user, desk bridge maintainer

## Context

The phone bridge accepted `/agent codex` and `/agent claude`, but a bare `/agent` only described the
current default and priority order. A user who wanted to choose manually had to remember provider
names, while a numbered chooser appeared only after an automatic availability failure. Manual choice
was also coupled to fallback behavior — pinning an agent disabled automatic recovery — which
conflated two orthogonal concerns.

## Decision

`/agent` opens a bridge-native numbered list of configured agent/model pairs. Every visible model has
its own number, so `/agent N` or a bare number within five minutes selects the exact default agent
and model for future runs. `/agent codex` and `/agent claude` open a focused model menu for that
agent instead of silently selecting an arbitrary model. The picker performs no model call and remains
usable while another run is active without interrupting it.

Each agent entry shows at most four models. Codex uses its live local catalog; Claude uses configured
candidates because its CLI has no equivalent catalog endpoint. Recent observed availability failures
and provider reset times override the passive list. "Configured; verified when selected" is not
presented as a live probe, and opening the menu never spends model quota.

Each observed rate-limit or availability failure is written to durable bridge state as soon as it is
seen. That record remains visible to `/agent` after a bridge restart or model handoff, until a real
run or reset probe verifies that exact model again.

Manual agent choice and automatic model recovery remain separate state machines. A pending model or
agent decision always owns a bare numbered reply before the manual picker; `/agent N` remains an
unambiguous manual selection. Choosing an agent does not disable future availability inquiries or
full-mode bounded automatic fallback.

## Consequences

- Phone users can discover and select an exact configured agent/model pair without memorizing command
  arguments.
- `/agent codex|claude` remains a concise way to browse one agent's available models.
- Existing automatic switch, `/decide`, queue, and active-run behavior remain unchanged.
- New obligation: the durable availability record must be cleared when a model verifies again, or a
  stale unavailable label could persist past a provider's recovery.
- The five-minute expiry limits accidental capture of unrelated numeric messages, but also means a
  deferred bare-number reply after that window is treated as normal input, not a selection.

## Alternatives considered

- **Keep `/agent` as a status/priority display and rely on the post-failure chooser** — rejected;
  manual selection should not require waiting for a failure to surface a numbered list.
- **Pin an agent and disable automatic fallback on manual selection** — rejected; deliberate choice of
  a default and passive availability recovery are orthogonal and should not be coupled.
