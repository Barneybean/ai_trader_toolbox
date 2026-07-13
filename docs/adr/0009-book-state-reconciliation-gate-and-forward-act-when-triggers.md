# ADR-0009: Book-state reconciliation gate and forward Act-when triggers

- **Status:** Accepted
- **Date:** 2026-07-12
- **Deciders:** desk maintainer, review

## Context

Two recurring failure modes surfaced when comparing desk runs from different agents on the same
pre-market session:

1. **Buying power read as free cash.** A run reported broker *buying power* as deployable "dry
   powder" and argued a cash-preservation thesis — while a material share of that cash sat reserved
   in live resting buy orders the run never pulled. Buying power already nets out reserved orders,
   so a low number can hide cash trapped in cancellable bids, and the actual highest-value action
   (cancel the conflicting bids) went unseen. The pipeline pulled positions and buying power but
   never reconciled **open orders**.

2. **Short-term-only judgment.** Deep dives scored the *trade* (levels, flows, valuation on
   trailing shape) while under-weighting what the *business is becoming* — the strategic pivots
   that re-decide what kind of company the market is pricing. `business-inflection.md` already
   inventoried such changes but stopped at description; it did not force a decision.

## Decision

We will add two methodology requirements to the base pipeline:

1. **Book-state reconciliation (SKILL Step 3b, hard gate, every run).** Before writing the orders
   section, pull open orders (`get_equity_orders` / `get_option_orders`) on the tradable account and
   decompose `net buying power = settled cash − cash reserved by open buy orders`. Report
   cash / reserved / net and every resting order; a resting order that fights the run's plan is
   itself a cancel/replace ticket. Never quote buying power alone as free "dry powder". Omitting the
   order pull or the cash split fails the sufficiency gate. Wired into the Action section and
   `skills/execution/data-and-execution.md`.

2. **Act-when triggers in `business-inflection.md`.** Every inflection row carries an "Act when"
   column — the observable proof + price level + date that flips the name from watch to a sized
   position or trim, written to the action-levels registry and catalyst map. An inflection read with
   no position, no dated trigger, and no explicit "priced in — no edge" verdict is unfinished.

## Consequences

- A report can no longer reason about cash posture while blind to resting orders; the highest-value
  action in an event-gated run (freeing reserved cash) becomes visible by construction.
- Forward business analysis must resolve to a decision on a clock, not narration.
- New obligation: the run spends connector calls on open-order state every cycle, and the Act-when
  column adds a required field to the inflection table (a name with a real pivot but no dated
  trigger now reads as incomplete rather than done).
- Failure mode created: an over-eager Act-when can register a level on a still-speculative pivot;
  the materiality gate and proof-over-promise rule remain the backstop.

## Alternatives considered

- **Leave order reconciliation to execution time.** Rejected — the analysis then sizes and argues
  cash against a wrong free-cash number; the error is upstream of execution.
- **Keep business-inflection descriptive.** Rejected — a forward read that changes nothing the desk
  does is color, not edge; the decision link is the point.
- **Make both advisory, not gated.** Rejected — advisory steps are the ones silently skipped; the
  comparison that motivated this ADR is exactly a skipped-by-default failure.
