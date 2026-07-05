# Mentor Casebook (starter template)

A **pattern library** of an investor you study — their dated calls and how they played out — to
*calibrate the desk's judgment*, not copy-trade. Ships empty on purpose: fill it with your own
material, or delete it. Keep anything private (a paid newsletter's live positions, a friend's book)
in a git-ignored `skills/private/` file.

## How to use it

Distill an investor's **repeatable philosophy and mechanics** into transferable rules — then log
their **dated calls** so the desk can check the method against reality.

## Philosophy checklist (fill in for your mentor)

- Entry — buy weakness vs. chase strength; scale-in vs. lump.
- Sizing — concentration cap, conviction tiers, cash policy.
- Risk — how they cut losers, hedge, take profits.
- Edge — what they see that the crowd doesn't (positioning, turnarounds, secular waves…).
- Holding — when they let winners run vs. rotate.

## Track-record log (a pattern library)

| Date | Ticker | Call (entry/target/stop) | Thesis (1 line) | Outcome (raw / vs SPY) | Lesson |
|------|--------|--------------------------|-----------------|------------------------|--------|
| _yyyy-mm-dd_ | _TICK_ | _buy $X → $Y, stop $Z_ | _…_ | _pending_ | _…_ |

Reconcile against live prices periodically — a method is only as good as how its calls aged. The
desk's own calls are logged separately by `scripts/track_record.py` (see
`skills/decision/reflection-memory.md`).

> **Privacy:** never commit someone's paywalled/members-only live positions. Distill the *method*
> (fine to share); keep the *positions* private.
