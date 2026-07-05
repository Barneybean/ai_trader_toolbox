# Accumulation, Distribution & Chip Distribution (institutional footprints)

Price is moved by **institutions accumulating and distributing** — retail loses by getting
**shaken out during accumulation** and **holding the bag during distribution.** The desk reads
the footprints: which phase a stock is in, where the "chips" (shares by holder cost-basis)
concentrate, whether smart money is quietly buying or unloading, and — the mentor's specialty —
**anticipating the shakeouts ("chip washes" / 洗盘) before a markup and accumulating into them
instead of being flushed.** Probabilistic — always confirm with volume/OBV and the fundamental
thesis; a wash in a broken business is just a decline.

Pairs with `skills/analysis/quant-levels.md` (levels/volume engine),
`skills/edge/smart-money.md` (insider buying *is* accumulation), `skills/edge/variant-perception.md`.

---

## First identify the PHASE (same setup is a buy or a trap depending on it)

Wyckoff cycle: **Accumulation → Markup → Distribution → Markdown.**
- **Accumulation** — basing *after* a decline; institutions absorb supply. Dull, range-bound.
  *Buy the shakeouts.*
- **Markup** — trend up; chips transferred to higher cost. *Ride; add on pullbacks to support.*
- **Distribution** — topping *after* a run; institutions unload into strength; churn at highs.
  *Trim/avoid.*
- **Markdown** — trend down; supply overwhelms. *Avoid; don't average a falling knife.*

Call the phase FIRST. "Cheap" in markdown is a knife; a dull base in late accumulation is the setup.

## Chip / cost-basis distribution

Shares by the price holders bought at. Read:
- **Concentration vs. dispersion.** **Single dense peak** after a long base = supply
  absorbed at one cost zone = accumulation likely complete = bullish. **Multiple peaks / heavy
  overhead** = trapped holders (套牢盘) above = resistance on the way up.
- **Chip migration.** Low-cost base chips **moving up** (via turnover/换手) into higher zones =
  markup underway (early holders sold to higher-cost buyers, float absorbed). Bottom
  concentration that won't break = accumulation still in progress.
- **Overhead supply.** Dense chips above price = "get out even" sellers; each rally meets supply
  until absorbed. Light overhead = clean runway.

**The desk computes it — `scripts/indicators.py` → `chip_distribution`.** Builds an actual
chip distribution from volume-at-price: walks daily bars, distributes each day's volume across its range,
and **decays older chips by turnover** (exact with `--float <shares>`; recency half-life
otherwise) so the profile reflects who holds *now*. Fields:
- **`main_cost_basis`** — zone with the most chips (主力成本 / big money's average). Below price
  = support shelf + profit cushion; **above price = overhead supply** (recent crowd trapped, caps rallies).
- **`secondary_peaks`** + **`high_volume_nodes`** — other dense shelves; strongest S/R and
  natural scale-in/out rungs.
- **`pct_in_profit` (获利盘) vs `pct_trapped_overhead` (套牢盘)** — float in gain vs underwater
  above price. Heavy trapped = every bounce meets "get me out even" selling until absorbed.
- **`concentration`** — **`concentrated`** (tight single peak) after a long base = supply
  absorbed = bullish; **`dispersed`** = spread wide = still churning / late-cycle = *not* a
  coiled base. Often separates a ready-to-launch accumulation from a name that just looks cheap.

Cross-check with **OBV** and the **S/R swing-touch clustering** — chip peak + multi-touch shelf
+ OBV turn coinciding = high-confidence. High turnover at a level = chips transferring
(accumulation if price holds, distribution if it stalls at highs).

## Accumulation tells (buy the base)

- Prior downtrend **exhausting**; selling climaxes, price refuses new lows.
- **Volume dries up** in the base, then **expands on up-days** (demand).
- **Higher lows**, narrowing range, long dull sideways action.
- **OBV rising while price flat** — smart money accumulating under cover.
- **Springs/shakeouts that quickly reclaim** support (below).
- **Insider open-market cluster buying** at the base (`skills/edge/smart-money.md`).

## Distribution tells (trim / avoid)

- **Churning at highs on heavy volume, no price progress.**
- **Upthrusts / failed breakouts** (UTAD): pokes above resistance that fail back into range.
- **OBV divergence** — price makes highs, OBV doesn't.
- **Heavy discretionary insider selling into strength** — the Robinhood-at-$150 pattern.

## The shakeout / "chip wash" (洗盘) — the mentor's edge

**Why:** before marking up, institutions **shake out weak/low-cost holders** to (a) cut overhead
supply that would cap the rally and (b) accumulate cheaper. A base is rarely clean — expect
**deliberate dips that look like breakdowns.**

**Wash vs. real breakdown:**
- A sharp dip **breaks an obvious support / round number / recent low** (*bear trap*) then
  **quickly reclaims** it (Wyckoff **spring**).
- Dip on **declining or non-confirming volume**, or a volume spike that snaps back same/next day (absorption).
- **OBV holds**; higher-timeframe base intact; thesis unbroken.
- Often **repeated** — a long boring base with multiple fakeouts that flush impatient holders.

**Trade it:** *expect* the washes and **scale in** rather than get shaken out. Confirm: reclaim
(spring) + OBV holding + thesis intact. Pre-commit invalidation — a **real markdown** (lower
lows on *rising* volume, OBV collapsing, thesis broken) is NOT a wash; stand aside.

## Timing the markup (when the "boost" comes)

Markup is near when accumulation looks **complete**: chips concentrated at the base (single
peak), volume dried then **expanding on up-moves**, price **reclaims and holds above the base and
the 50-DMA**, OBV to new highs, overhead absorbed. "Expect a couple more washes before it's
boosted" = base **immature** — still accumulating; be patient, buy the flushes.

## The judgment to produce (per name)

1. **Phase call** — accumulation / markup / distribution / markdown, with evidence (price
   structure + volume + OBV + chip/S-R concentration).
2. **Chip read** — where concentration and overhead supply sit; is the base holding.
3. **Wash vs. markdown** — more shakeouts likely (base immature), markup near (complete), or a
   genuine markdown to avoid?
4. **Accumulation plan** — scale-in levels to buy the washes, the spring-reclaim confirmation,
   the invalidation (base failure).

## Worked example — NKE (the mentor's read)

After a long markdown from ~$80 to the low-$40s, NKE is **basing** (accumulation) — and the
**insider cluster buying at $42–43** (CEO Hill, dir. Cook, ex-Intel-CEO Swan) is a textbook
accumulation footprint. The read: **expect a couple more chip washes in the low-$40s / high-$30s**
— deliberate flushes below the obvious $42/$40 supports to shake out weak hands and absorb
overhead — **before** the markup; accumulate *into* them. The markup thesis (multi-quarter
earnings turnaround + **2026 World Cup** tailwind + **DTC→wholesale pivot** under a CEO with deep
wholesale roots + a **CFO change** Wall Street should welcome) targets **~$90–100 over ~6 months**
once accumulation completes and NKE reclaims and holds. **Invalidation** (markdown, not wash): a
weekly close well below $40 on *heavy* volume with OBV breaking down.

**Guardrails:** probabilistic — always confirm with volume + OBV, distinguish wash from
markdown, and only apply where the fundamental thesis supports accumulation.

