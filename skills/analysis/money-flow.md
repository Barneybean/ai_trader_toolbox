# Unusual Money Movement → Impending Large Move (flow detector)

Before a large move, money leaves a footprint: **direction** shows up as buying/selling
pressure (where price closes in its range × volume) and as **divergence** (price flat/down while
volume-flow rises = accumulation *under cover*); **magnitude** shows up as **volatility
contraction** — a stock coils (tightening range, drying volume, a squeeze) before it expands. This
skill reads both and answers the user's question directly: *is this name set up for a large move,
which way, and what confirms it?*

Powered by **`scripts/analysis/flow_anomaly.py`** (pure stdlib, reuses `indicators.py`). Pairs with
`skills/analysis/chip-distribution.md` (the ownership gate + who-holds-it read is REQUIRED here —
see below), `skills/analysis/quant-levels.md` (the S/R the move breaks from),
`skills/edge/smart-money.md` (insider buys *are* accumulation). Probabilistic on a volume-only
proxy — it can't see dark/off-exchange prints; confirm, don't obey blindly.

---

## What the engine outputs

Run: `python3 scripts/analysis/flow_anomaly.py <historicals.json> --price <live> [--options opt.json]`

- **`flow_pressure` −100…+100** — signed net pressure. Blend of CMF(20), MFI(14), A/D-line slope,
  the sign of the most *unusual*-volume recent bar, and (if supplied) options lean. +ve =
  accumulation, −ve = distribution. |value| ≥ 25 = a real tilt, not noise.
- **`coil_energy` 0…100** — how loaded the spring is. Bollinger-in-Keltner squeeze + band-width
  percentile (how tight vs its own history) + ATR contraction + volume dry-up. ≥ 55 = coiling; ≥ 70
  = tightly coiled. **This is the magnitude/imminence gauge** — big moves come out of tight coils.
- **`verdict`** — the call:
  - **COILED_BULLISH** — energy loaded + net buying → large UP setup. *Buy the base / breakout.*
  - **COILED_BEARISH** — energy loaded + net selling → large DOWN risk. *Avoid / trim / hedge.*
  - **COILED_UNDIRECTED** — energy loaded, pressure mixed → *wait for the break* (don't pre-position).
  - **EXPANSION_UP / EXPANSION_DOWN** — volume already expanding with pressure → *move underway*
    (don't chase late; act only on a confirmed hold beyond the trigger).
  - **PRESSURE_BUILDING_UP/DOWN** — directional flow but no coil yet → watchlist, not a trade.
  - **NEUTRAL** — no unusual money movement.
- **`confidence`** (low/med/high) = how many independent signals agree (`signals_agree` "4/4").
  One indicator is a guess; four pointing the same way is a read.
- **`triggers`** — `breakout_above` / `breakdown_below`: the level a close-beyond confirms the move.

## The component reads (what each is telling you)

- **CMF / A/D-line / MFI** — buying vs selling pressure from *where in the range* each bar closes,
  volume-weighted. Persistent positive CMF in a flat base = quiet accumulation.
- **Volume z-score & signed surge** — statistical unusualness (z>2 ≈ top ~2.5% of days), and
  crucially its *direction*: a z=3 surge on an up-close bar shows demand's hand; on a down-close
  bar, supply's. More honest than a fixed "1.5× average."
- **Effort vs result (Wyckoff absorption)** — heavy volume + tiny price move = someone big
  absorbing. At/near support → bullish (demand soaking supply); at/near resistance/highs → bearish
  (supply capping). The single most useful "smart money is here" tell.
- **Divergence** — price down while A/D + OBV rise = **accumulation under cover** (bullish, the
  highest-value early tell); price up while flow falls = **distribution under cover** (bearish —
  the Robinhood-at-$150 pattern before the round-trip).
- **Squeeze/coil** — the energy gauge. A stock can't stay tightly coiled forever; it resolves with
  a large move. Coil says *a big move is coming*; pressure/divergence says *which way*.

## Options flow overlay (source it, then pass it in)

`flow_anomaly.py` can't fetch options — the agent pulls a snapshot via the **Robinhood MCP** tools
and passes it with `--options`. Pull for the name (and its near-dated chain):
- `get_option_chains` / `get_option_instruments` → strikes, expiries, open interest.
- `get_option_quotes` / `get_option_historicals` → per-contract volume, IV, bid/ask.
- Derive and write a small JSON: `put_call_volume_ratio`, `put_call_oi_ratio`, `iv_rank`,
  `iv_change_pct`, `skew_25d` (25Δ put IV − call IV; +ve = downside fear priced), and a free-text
  `unusual` note (e.g. "repeated Sep 55c sweeps 2–4× OI"). Any subset works.

Read it: **call-heavy volume + falling/negative skew + rising IV on a coil** corroborates
COILED_BULLISH (speculators positioning for an up-move); **put-heavy + positive skew + IV spike**
corroborates downside. Unusual sweeps 2–4× open interest at a strike = someone with size and a
view — note the strike/expiry as a magnet. Guardrail: IV expansion alone just means *a* move is
expected (often earnings), not the direction — let skew/flow set direction.

## Decision rubric — up vs down, and how hard

1. **Ownership gate FIRST** (`skills/analysis/chip-distribution.md`). *Whose stock is this?* The
   whole footprint model assumes institutions set the price. Institution-heavy (≳70% float) →
   trust the reads. Retail/believer-heavy (TSLA, memes) → **downweight** flow/coil mechanics
   (believers don't sell shakeouts; "distribution tops" keep reclaiming); upweight
   catalysts/sentiment/gamma. Tiny float → moves violent both ways, size down.
2. **Coil + pressure + confidence together.** Trade the setup only when `coil_energy ≥ 55`,
   `|flow_pressure| ≥ 25`, and `confidence ≥ medium` **agree**. COILED_UNDIRECTED = wait; don't
   guess direction into a coil.
3. **Confirm at the trigger.** A coil is potential energy; the **break beyond the trigger on
   rel-volume > ~1.8×** is kinetic. Don't call a "large up move" until price confirms — pre-position
   small in the base only when divergence/absorption/insider-buys already lean your way.
4. **Locate it on the phase map.** COILED_BULLISH is highest-quality in **late accumulation** after
   a base (chip concentration tight, insiders buying); COILED_BEARISH in **distribution** after a
   run. A "coil" mid-markdown that resolves *down* is not a buy — the coil gauge is direction-blind
   by itself, which is why pressure + phase gate it.
5. **Size to the invalidation.** The opposite trigger is a clean stop (coiled-bullish invalidates on
   a close back below `breakdown_below`). Tight coils give tight, well-defined risk — that's the edge.

## Feeds the desk

- **Two-horizon call (`SKILL.md`):** the short-run direction/target and wash-likelihood come
  straight from the verdict + triggers; a COILED read with a near catalyst is a dated short-run setup.
- **Quant role (`skills/decision/roles.md`):** report `verdict / flow_pressure / coil_energy /
  confidence` alongside the S/R map and chip read; flag any divergence explicitly.
- **Chip-wash timing:** a COILED_BULLISH that keeps flushing supports then reclaiming (spring) on
  drying volume = the mentor's "expect a couple more washes before the boost" — accumulate into it.
- **Risk (`skills/decision/risk-committee.md`):** COILED_BEARISH / EXPANSION_DOWN on a held name =
  trim / tighten / hedge trigger, even if the story is still good.

## Guardrails

- **Volume-only proxy** — no dark-pool/off-exchange visibility; treat as ranges, corroborate with
  chips + insider filings, never as a lone trigger.
- **Coil ≠ direction.** Energy loaded says *a* big move; pressure + phase + confirmation say which.
- **Degrades honestly** — no volume in the feed → money-flow reads are unavailable (the JSON warns);
  no high/low → range reads degrade to closes. Say so; don't fabricate a pressure number.
- **Not every coil fires soon** — some stay tight for weeks; the trigger + a stop keep you from
  paying to wait.
