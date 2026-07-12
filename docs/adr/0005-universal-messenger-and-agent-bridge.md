# ADR-0005: Universal messenger and agent bridge

- **Status:** Accepted
- **Date:** 2026-07-12

## Context

Phone access began with one working message provider and one agent runtime. The toolkit now needs
Telegram, Discord, and WhatsApp transports without duplicating desk commands, and it must continue
work when an agent is unavailable without leaking or corrupting sessions.

## Decision

`chat-bot-bridge/` is the sole bridge directory. Official provider APIs implement one transport
contract for text, files, typing, polling/webhooks, and sender allowlists. Provider and agent
priority are configurable. Codex and Claude retain separate session IDs; availability failures may
trigger a bounded recent-context handoff, but investment disagreement never triggers fallback.
Runs are serialized. Public templates contain blank credentials, generic plist labels, neutral
schedule examples, CLI-resolved binaries, optional model overrides, and `manual` execution mode.

Private `.env`, state, sessions, logs, customized plists, paths, schedules, and subscription data
never cross the open-source boundary.

## Consequences

- Adding a message app requires an adapter, not another bridge directory.
- Agent fallback preserves continuity without merging provider sessions.
- Setup requires users to customize local templates before installing services.

## Alternatives considered

- One directory per app—duplicates commands, safety rules, and session logic.
- Copy the maintainer's live bridge—would publish machine state and unsafe defaults.
