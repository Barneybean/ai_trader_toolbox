# Value Radar — hunting the ≥30% mispricing

The desk's bar for deploying *new* capital into a value idea: the path to **at least +30%**
must be arithmetic, not adjectives — and the entry must be *washed*, because a cheap stock
that never flushed has no forced seller to buy from. `scripts/analysis/value_radar.py` turns the
desk's underwritten inputs into a ranked, falsifiable screen.

## Why 30%

Below ~30% upside, being roughly right isn't enough: slippage on the entry, a soft quarter,
one multiple-point of compression, or plain opportunity cost eats the trade. 30% to a
*defensible median fair value* leaves room to be 10% wrong twice and still beat the index.
It also forces honesty: most "undervalued" pitches die at the arithmetic stage — which is
the point (edge or silence).

## The funnel (where candidates come from)

Run the hunt where mispricings actually live, not down the S&P alphabetically:

1. **TURNING / NEGLECTED sectors** from `scripts/analysis/rotation_radar.py` — value with a
   rotation tailwind beats value in a falling-knife sector.
2. **Washout lists** — names ≥20–40% off their 52-week high where the *business* didn't
   shrink with the price (revenue/backlog intact; multiple did the falling).
3. **Insider clusters** — open-market buys near lows (`skills/edge/smart-money.md`).
4. **Post-overreaction events** — the catalyst scan's ±3% attribution finds sessions where
   the move exceeded the news (`skills/analysis/catalyst-scan.md`).
5. **The mentor book's buy wings** — underwrite independently, never copy-trade.

## The three legs (the script's math — the desk supplies the inputs, cited)

Fair value = **median of ≥2 independent legs**. One model can be argued into any answer;
the median of three disciplines can't be quietly gamed.

- **Leg A — owner-earnings DCF.** PV of the desk's *underwritten* growth (via
  `reverse_dcf.py` engine, r=10%, terminal 2.5% defaults). The radar also prints the
  growth **the price implies** — when implied ≪ underwritten, that gap *is* the thesis.
- **Leg B — mature comparable.** Normalized EPS × what a *mature* peer of this quality
  trades at (`industry-map.md`'s mature-comparable yardstick). Normalized ≠ trough ≠ peak:
  use the earnings power once the current distortion (inventory glut, ramp costs, cycle
  trough) clears — and write down *why* that number, with the filing that supports it.
- **Leg C — own-history reversion.** Normalized EPS × the midpoint of the stock's own
  5-year multiple band. Catches "cheap vs itself"; blind to regime change — which is why
  it never stands alone.
- **Bear floor (strongly encouraged).** Bear EPS × bear multiple. If the bear case costs
  more than ~20%, the position sizing math breaks regardless of upside — WAIT.

**Input honesty is the whole game.** Every `eps_norm`, `growth`, `mature_pe` is a desk
judgment that must carry a citation (filing, transcript, comp table) in the report's
evidence trail. The radar ranks judgments; it cannot launder bad ones.

## The entry gate (cheap ≠ buy)

- **WASHED** — ≥20% off the 52-week high. No flush = no forced sellers = the desk is the
  exit liquidity for someone smarter.
- **BASING** — OBV accumulating over ~60d or price reclaiming SMA50. Cheap-and-knifing is
  `WAIT-KNIFE`: register an action level at the shelf instead
  (`journal/action-levels.jsonl` — let the level do the buying).
- Then the standard gauntlet still applies: **quality gate** (`quality_gate.py` — the
  7 disqualifiers), **catalyst map** (undervalued needs a *why now*: a dated event that
  forces the re-rate — earnings, restructuring proof, cycle data), bull/bear debate,
  risk committee. The radar is a *finder*, not an approver.

## Sizing & the two-horizon statement

A cleared BUY-CANDIDATE is still stated in desk grammar: short-run call (the base/flush
mechanics, weeks) + long-run call (the re-rate path to fair value, 6–18mo, **with a
clock**: what catalyst re-rates it, by when — "cheap forever" is dead money, log a `flat`
insight if the clock is unclear). Size by conviction tier and the rubric; DEEP_VALUE
(≥50%) earns tranches, never all-in (the extra upside usually means extra uncertainty).

## Guardrails

- **Value traps are the failure mode.** Trap tells: bear floor breached, quality gate
  disqualifier (dividend > EPS, refinancing wall, secular unit decline), implied growth
  *negative* while the desk underwrites heroics, management response COSMETIC on every
  headwind. Two tells = pass, whatever the upside says.
- **Don't average a WAIT-KNIFE down.** Re-run the radar when the level triggers.
- **Log it either way** — every VALUE_30+ that gets passed goes to the journal with the
  reason; the scorer will tell us if the gate is too tight.
