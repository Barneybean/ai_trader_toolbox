# Sell Timing — ride the popular stock, leave before the give-back

House view, promoted to desk doctrine: **popular stocks run further than fair value
says they should — and then retrace faster than anyone plans for.** The error is
symmetric: selling a runner early costs the melt-up; overstaying costs the round-trip.
This skill times the exit on **extended / popular / momentum names** — a broken *thesis*
exits on the thesis (`skills/edge/thematic-waves.md` contrast rule), not on this chart
radar. Engine: `scripts/exit_radar.py`.

## The core asymmetry

On a popular name the crowd IS the fuel: valuation stops mattering on the way up
(fade-the-multiple shorts get run over) and stops mattering on the way down (support
built on momentum money evaporates). So the desk **never argues valuation on a runner,
in either direction** — it rides the trend and watches for *distribution tells*: the
footprints institutions leave when they hand inventory to the crowd near the top.

## The six tells (`exit_radar.py` scores each; ≥2 firing = the top is forming)

1. **EXTENSION** — price ≥6 ATRs above SMA50 at a ~90th-percentile extreme *for this
   name*. Stretched rubber bands snap back; extension marks where trims get paid best.
2. **DISTRIBUTION** — ≥4 heavy-volume down days in 25 sessions. Single red days are
   noise; clusters are institutions selling into strength.
3. **OBV DIVERGENCE** — price prints a new high the flow refuses to confirm. The last
   push is retail; the smart money already left.
4. **CLIMAX** — a 95th-percentile 5-day burst on ~2× volume. Blow-off velocity is the
   crowd arriving all at once; there's no one left to buy after them.
5. **SATURATION** — ≥90% of chips in profit. When everyone's a winner, everyone's a
   potential seller; the first dip has no defenders (`chip-distribution.md`).
6. **GIVE-BACK** — the position has surrendered ≥⅓ of its **peak** gain. This is the
   hard guard the whole skill exists for.

## The verdict ladder (pre-committed, not negotiated in the moment)

| Verdict | Tension | The move |
|---|---|---|
| **RIDE** | <25 | Hold. Stop lives at the chandelier (22d high − 3×ATR). Don't trim a working runner out of boredom. |
| **TIGHTEN** | 25–49 | Raise the stop to the printed chandelier. **No new adds.** Decide *now* what you'll sell at TRIM. |
| **TRIM** | 50–74 | Sell ¼–⅓ **into strength** — resting limit *above* market, not a market-order dump into a dip. Repeat on each new tell. |
| **EXIT** | ≥75, or hard break | Close below chandelier *and* SMA50 = the run is over. Sell; don't negotiate with a level that already broke. |

**Sell into strength, always.** The whole edge of *timing* the exit is that you sell to
the crowd while it's still buying. Waiting for the break means selling with the crowd —
same shares, much worse price.

## The give-back rule (never round-trip a winner)

> Never surrender more than **⅓ of the peak gain** on a popular-stock ride.

At +30% the floor is ≈ +20%; at +100% it's ≈ +67%. Mechanics: once a position is up
≥30%, log the peak, set the give-back level, and *raise it* with every new peak — a
ratchet, never lowered. Pair with the profit ladder (`strategies.md`): scale-outs at
pre-set targets convert paper gain into realized gain so the ratchet protects a smaller
remainder. This rule is what "cautious on selling timing before it retraces" means in
numbers.

## Cadence & wiring

- Run `exit_radar.py <ticker> --entry <avg cost>` on **every holding up ≥30%** and every
  position tagged *spiker/popular*, at every desk run. Report the verdict per name.
- A TRIM/EXIT verdict on a held name is an action item in the report — with the ladder
  levels printed, never "consider trimming."
- Rotation context stacks: COOLING on the name's sector (`rotation_radar.py`) adds
  urgency one notch (RIDE→TIGHTEN, TIGHTEN→TRIM) — sector cracks front-run name cracks.
- Earnings inside ~2 weeks on an extended runner: take the TRIM early (sell-the-news
  discipline, `catalyst-scan.md` Tier S) — binaries and blow-off tops compound badly.
- Log every exit call as an insight (`insight-registry.md`, method tag `exit-radar`) so
  the scorer proves whether the radar actually beats holding.

## Guardrails

- **Definers are not spikers.** A secular definer in drawdown follows trim-to-base
  (never to zero); this radar times *popular-stock rides* and tactical winners. Tag the
  position type at entry, not at the exit moment.
- **Tax awareness, never tax paralysis** — a TRIM near long-term status can wait days
  (`tax-aware.md`), an EXIT waits for nothing.
- The radar can be early — that's its job. Being flat for the last 10% of a blow-off is
  a fee, not a failure; the round-trip you didn't take is the payment.
