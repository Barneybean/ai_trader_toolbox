# ADR-0039: Rolling position management is an audited plan

- **Status:** Accepted
- **Date:** 2026-07-18
- **Deciders:** User, toolkit maintainer

## Context

The desk already recommends cash discipline, staged entries, and trims into strength, but it had no
deterministic way to prove that repeated trading improved after-cost portfolio value. Optimizing for
share count can hide underperformance, while embedding personal ledgers in reports or public fixtures
would violate the toolkit's privacy boundary.

## Decision

We will provide `scripts/analysis/position_manager.py` as a standalone, Python-stdlib-only advisory
engine. It will consume an explicit local JSON ledger, use documented average-cost accounting,
compare ending value with an all-in buy-and-hold benchmark, and cap optional staged adds by available
cash, per-name concentration, and entry-to-stop account risk. It will reject irreconcilable ledgers
and impossible stop geometry, persist nothing, fetch nothing, and place no orders.

Rolling-position analysis remains optional and triggered by a supplied ledger. The engine verifies
the math of user- or desk-underwritten levels; it does not create a predictive signal. Public tests
and documentation use fictional inputs, while real holdings and transactions remain local and
git-ignored. The deterministic regression contract lives in
`scripts/analysis/test_position_manager.py` and the significant-change smoke gate runs it whenever
the engine or its tests change.

## Consequences

The desk can now distinguish actual after-cost value-add from a larger share count and can produce a
repeatable tranche budget that respects the existing risk constitution. Users must provide a
complete ledger and benchmark start price, and average-cost results must not be mistaken for tax-lot
or tax advice. Incorrect or hindsight-selected levels can still make a weak strategy look good, so
the ordinary research, sufficiency, tax, and execution gates remain binding.

## Alternatives considered

- **Leave the calculation in agent prose** — rejected because arithmetic and benchmark treatment
  would vary between runs and could not be regression-tested.
- **Persist a canonical portfolio ledger in the public toolkit** — rejected because it introduces
  sensitive state, migrations, and a second source of truth beside the broker.
- **Put the calculator in the execution gateway** — rejected because plan analysis must not acquire
  broker authority or blur the gateway's validate-only ticket contract.
