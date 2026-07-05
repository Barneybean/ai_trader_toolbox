# Quant Analysis — Levels, Indicators, and Edge Math

The Quant playbook: turn `scripts/indicators.py` output into a defensible read of **support
(floor)** and **resistance (upper "pressure")**, then a numeric edge the CIO gate can trust.
Replace "looks bullish" with levels, vol-scaled risk, and a reward:risk number.

Run the script first — never eyeball. Feed ~1yr of daily bars:
`python3 scripts/indicators.py <historicals.json> --price <live quote>`. Pass `--price` when
open so the S/R map centers on current price, not yesterday's close.

---

## 1. Support & resistance — the "pressure" map

`support_resistance` is the core deliverable.

- **`nearest_support`** = closest price *below* current where buyers stepped in.
  **`nearest_resistance`** = closest *above* where sellers capped it (**upper pressure**). Each carries:
  - `level` — the clustered price *zone*, not a single tick.
  - `touches` — independent swing pivots forming it. **More = stronger.** 3-touch = real
    overhead supply; 1-touch = soft.
  - `distance_pct` — distance from price. Tight to resistance = little room; tight to support = tight risk.
- **`resistance_ladder` / `support_ladder`** — next levels up/down; scale-out rungs and the
  next floor if the first support fails.
- **How built:** fractal swing highs/lows (pivot = local extreme over the window), clustered
  within ~0.6×ATR. Volatility-aware — a $400 and a $4 stock both get sensible zones.

**Confluence makes a level tradable** — multiple independent methods on the same area.
Cross-check swing S/R against:
- **Moving averages** (`sma_20/50/200`) — dynamic S/R; price bounces/stalls at a rising
  SMA50/200. House view "reclaim and hold the 30-day MA after a washout" lives here (SMA20 ≈ 30-session line).
- **Bollinger bands** — lower = mean-reversion support in a range, upper = stretch/resistance.
  `percent_b` <0 or >1 = outside the band (extended).
- **Pivot points** (`P/R1-3/S1-3`) — floor-trader levels off the last bar; Tactical's near-term refs.
- **Fibonacci** — post-move, 0.382 / 0.5 / 0.618 = common pullback-support (uptrend) or
  failed-bounce (downtrend).
- **52-week high/low and round numbers** — psychological levels that concentrate orders.

Report **strong** when swing-touches + ≥1 of {MA, pivot, fib, round number} coincide within
tolerance; **soft** when only one method sees it. Say which: "resistance ~$129 is strong
(3 swing touches + falling SMA50 + prior gap)."

---

## 2. The indicator stack — what each is *for*

Don't dump every number. Each answers one question; use as a layered filter.

| Layer | Indicator (in output) | Question | Reading |
|---|---|---|---|
| **Trend** | SMA 20/50/200, EMA 12/26 | Direction, aligned? | Price>SMA50>SMA200 = clean uptrend. Golden/death crosses = regime changes. |
| **Trend strength** | ADX / +DI / −DI | Trend or chop? | ADX>25 = trending (trade with it); ADX<20 = range (fade extremes). Direction from +DI vs −DI. |
| **Momentum** | RSI(14) | Stretched, diverging? | >70 overbought, <30 oversold. **Divergence** (price new high, RSI lower high) warns of exhaustion. |
| **Momentum** | MACD(12,26,9) | Turning? | `fresh_cross` = same-day signal-line cross (actionable), not just "bullish". |
| **Momentum** | Stochastic %K/%D | Where in range? | <20 oversold / >80 overbought; %K crossing %D up from oversold = swing trigger. |
| **Volatility** | ATR(14), `atr_pct` | Daily move size? | Sizes stops/targets. `atr_pct` = 1%/day vs 6%/day name. |
| **Volatility** | Bollinger(20,2), `width_pct` | Squeeze or expansion? | Narrow = coiled (breakout pending); wide = already moving. |
| **Volume** | Relative volume, OBV | Confirmed by participation? | `rel_volume`>1.5 = conviction; OBV `accumulation`/`distribution` = who's winning. House view: volume expansion → reversal/breakout tell. |

**Regime dictates the playbook. Read ADX first:**
- **Trending (ADX>25):** trade *with* it. Buy pullbacks to support/rising MA; sell rips only to
  trim. Breakouts more likely to hold.
- **Range/chop (ADX<20):** mean-revert. Buy support, sell resistance, fade RSI extremes.
  Breakouts likely to fail — demand volume confirmation.

---

## 3. From levels to a trade — the edge math

`trade_scaffold` is a **starting frame**, not the order. It computes a long-side stop/target as
a vol-anchored default; the PM adjusts.

- **Stop** = tighter of `1.5×ATR` below entry or just under nearest structural support. Outside
  daily noise, respects the real floor. A stop is a **dollar statement of risk**
  (`skills/decision/strategies.md`).
- **Target** = nearest resistance zone (where moves statistically stall). Stack more on
  `resistance_ladder` for scale-outs.
- **Reward:Risk = `reward_risk`** = `(target − entry) / (entry − stop)`. **Hard gate: RR ≥ 2.0
  net of costs** (`skills/decision/review-rubric.md`). RR<2 — usually price under heavy
  resistance — means *the entry is bad here*: wait for a pullback to support, or pass. Don't
  widen the target past a real level.

**EV, not just RR:** `EV ≈ p_win × reward − (1 − p_win) × risk`. Anchor `p_win` in setup + regime:
- Trend-continuation pullback in a strong uptrend (ADX>25, off rising SMA + support confluence,
  volume confirming): ~50–60%.
- Counter-trend / knife-catch / breakout in chop: ~35–45% — demand bigger RR. 3:1 at 40% is
  strongly +EV; 1.5:1 at 45% is not.
- **Validate against this name's own history** (`skills/decision/strategies.md`): before trusting
  "RSI<30 bounces here," check past oversold points in the historicals. If it didn't hold, distrust it.

**Size follows the stop.** Per-idea 2% risk cap: `shares = (0.02 × account) / (entry − stop)`.
Check against the concentration cap (`skills/decision/review-rubric.md`). Show the math.

---

## 4. The quant writeup (what the role hands the desk)

Per candidate, a tight block the PM and CIO can act on:

1. **Regime & trend:** primary trend (MA alignment), ADX strength/direction — one line.
2. **Setup:** trend-continuation / breakout / pullback / mean-reversion / none.
3. **Lower support:** nearest zone + strength (touches + confluence) + distance.
4. **Upper pressure:** nearest zone + strength + distance. Name the ceiling.
5. **Momentum & volume:** RSI/MACD/Stoch state, divergence; volume confirming (OBV)?
6. **Trade frame:** entry zone, ATR/structure stop, target ladder, the **RR number**, one-line
   EV/probability check.
7. **Timing verdict:** *now* / *wait for level X* / *no*. Say "good name, wrong price — wait for $X."

Separate **fact** (computed numbers) from **judgment** (interpretation). Flag degraded data: no
high/low in the feed → summary carries a WARNING and ATR/ADX/Stoch/S-R are approximated from
closes — say so, lower confidence.

