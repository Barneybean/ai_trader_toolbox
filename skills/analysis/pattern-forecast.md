# Pattern forecast — quantify the odds of the next move

**When:** a name is coiling (Bollinger band narrowing) or testing a support/resistance
level repeatedly, and someone asks the real question — *"which way does it break, and
by how much?"* Answer it with numbers, from the data, not with a hunch. Engine:
`scripts/forecast.py`. This is how the desk earns the word **confident**.

## What it computes (three independent lenses)

1. **Structure — is it actually coiled and tested?**
   - Bollinger band width at each bar → the **current width's percentile** vs the name's
     own history. Bottom tercile = a real squeeze (volatility contraction precedes
     expansion). Reports "20th percentile = coiled," not just "looks tight."
   - The **support being tested** and how many discrete bars **touched** it, plus the
     nearest **overhead** and its touches. Repeated tests are the setup.

2. **Historical analogs — the empirical base rate.** Scans this symbol's own history
   (and any `--peers` you add) for past bars in the **same state** — band squeezed into
   its lower tercile *and* price sitting on a multi-touch support — then measures what
   actually happened over the next `--horizon` days: **UP% / DOWN%**, median & mean
   forward return, the p10…p90 spread, and the average win vs average loss (the skew).
   A base rate beats a rule of thumb.

3. **Monte-Carlo — the forward distribution.** Block-bootstraps the recent daily
   log-returns (blocks preserve vol-clustering / autocorrelation a squeeze carries) over
   thousands of paths and reports:
   - **P(up) / P(down)** and the **expected & median move**;
   - the **terminal-price cone** (p10 / median / p90);
   - **first-passage**: P(it tags the breakout trigger *before* the breakdown trigger).
     Pass the real local levels with `--breakout` / `--breakdown` — otherwise a far
     default level makes first-passage meaningless (it'll "hit" the nearer level first
     by geometry, not by direction).
   - `--drift <annual>` injects a **fundamentals view** (e.g. a sanction headwind at
     `-0.18`) so you see the setup **chart-only** *and* **chart + view** side by side.

## How to read it (the discipline)

- **Separate the clocks.** The *first move* and the *pattern resolution* often disagree.
  First-passage can favor a **downside flush into a tested shelf** (a 4×-tested level is a
  *weakening* shelf — each test spends buyers) while the analog base rate favors an
  **up resolution** afterward (coiled-spring-off-support). Saying *"down first, then up"*
  with the probabilities attached **is** the edge — it tells you to **stage into the
  flush, not chase**.
- **Magnitude, not just direction.** Quote the cone (p10/median/p90) and the asymmetry
  (avg win vs avg loss). A 55% up-rate with +12% wins vs −5% losses is a very different
  trade from a 55% up-rate with symmetric payoffs.
- **Price the view.** Run it flat *and* with `--drift` for the fundamental risk. If the
  headwind flattens a bullish setup to 50/50, the honest read is "no edge chasing here —
  the edge is buying the level the model expects."
- **Vol scales everything.** A high annualized vol (e.g. 76%) means a wide cone and a real
  fat tail — size for it (wider stop, smaller clip), don't fake precision.

## Output → recommendation

Fold it straight into the report's per-stock **Forecast** block and the trade plan:
state P(up)/P(down), the expected/median move and cone, the first-passage read, then the
**odds-based plan** — where to stage, the stop wide enough for the modeled tail, the target
ladder, and a split confidence ("**high on the plan, low on timing the exact low**").

```
python3 scripts/forecast.py MP.json --price 53.48 --horizon 20 --sims 30000 \
        --breakout 60.19 --breakdown 51.63 --drift -0.18 --peers NVDA.json,TSLA.json
```

**Feed it deep history.** The Robinhood connector gives only ~1y of bars; base rates and the
bootstrap sharpen with more sample. Pass a **bare ticker** (subject *or* `--peers`) and it pulls
multi-year daily bars from Yahoo automatically — `forecast.py MP --price 53.31 --peers ALB,SQM` —
or pre-fetch with `scripts/yahoo.py MP --range 5y --out reports/data/MP.json`. Pick *pattern-kin*
peers (same coil-on-support behaviour, e.g. lithium miners for MP) to widen the analog pool. One
caveat: the **squeeze percentile is lookback-dependent** — a band tight against the last year can be
mid-pack against five — so name the window when you cite it, and don't let a longer lookback quietly
downgrade a genuine near-term coil.

Related: `[[quant-levels]]` (the S/R map it reads), `[[chip-distribution]]` (the cost-basis
shelf that makes a break decisive), `[[money-flow]]` (flow_pressure / coil_energy — the
*direction* pressure the coil will likely resolve toward), `[[variant-perception]]` (the
`--drift` view is your differentiated fundamental call, priced).
