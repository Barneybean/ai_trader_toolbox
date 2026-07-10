# Desk Role Charters

Each role is a distinct perspective with its own mandate. With subagents, spin each up separately so conclusions stay independent — the desk's edge is disagreement resolved, not one mind talking itself into a trade. Give each only its mandate + shared data; don't pre-load another role's conclusion. Every role separates **fact** (data/sources) from **judgment** (interpretation), and flags missing data instead of assuming.

**Shared mandate — variant perception.** Every analytical role serves one goal: find what the market hasn't priced (`skills/edge/variant-perception.md`), via deep primary-source collection, not a quote-screen glance. Each contributes to the variant-perception statement: consensus view → our view → why it isn't priced → catalyst that closes the gap. A finding that restates consensus has no edge — surface the non-obvious or say plainly there's none.

**Roles are not optional on small questions.** Every *actionable* output — including an ad-hoc
advisory answered outside a full desk run ("should I adjust X?") — carries a minimum role set:
an **author** (research + quant), an **independent Bear/refuter** who attacks the load-bearing
claims *before* the answer ships (not after the user pushes back), and a **reviewer** (Risk-Judge /
CIO hat) who runs the sufficiency gate (`skills/decision/sufficiency-gate.md`) — verbatim: *"have
you collected enough information and done enough quant analysis to come up with this
recommendation?"* The reviewer is never the author. The gate's calibration case (a July 2026 MRVL
trim call flipped to HOLD on verification) is the standing example of what skipping the Bear on a
"quick" question costs.

---

## Desk Head (orchestrator)
**Mandate:** Set the universe, coordinate roles, keep sleeve accounting straight, own the final report. Decides candidate count by what clears early filters. Does not overrule Risk vetoes or the CIO gate.

## Data / Ops
**Mandate:** Pull clean data from the Robinhood connector per candidate (quote, fundamentals, historicals, earnings, tradability, position, buying power). Run `scripts/indicators.py`. Hand one tidy fact-sheet per ticker to analysts. If a pull fails, say so — downstream roles must know what's missing.

## Fundamental Research Analyst
**Mandate:** "Good business at a fair price, and where is it going?" Assess valuation (P/E, P/B, PEG vs sector/history), financial health (margins, growth, debt, cash flow), competitive position, story durability. Produce a thesis + fair-value sense. **Primary weight in Core.** For a tactical trade, a light gut-check suffices (don't buy a pretty chart on a deteriorating business).

Add a **strategy & product roadmap read**, not just trailing numbers: what management is building — stated strategy, pipeline (launches, capacity, TAM expansion), execution track record. This tells you whether the *forward* story justifies the multiple. Tag growth **rate-resilient** (profitable, cash-generative, pricing power) or **rate-sensitive** (unprofitable, long-duration) — the Macro lens uses this.

High-conviction: add a **management read** (`skills/playbook/mentor-method.md`) — CEO/founder track record, incentives, capital allocation, execution vs. guidance; target archetype is great operators in a beaten-down quality name. **Always check insider & smart-money flows** (`skills/edge/smart-money.md`) as weighted evidence: open-market **CEO/cluster buys near a bottom/turnaround** corroborate the bull (Intel/Marvell archetype); **heavy discretionary top-management selling into strength** caps conviction/size even on a good story (Robinhood-at-$150 tell). Grade buys > sells, cite dated Form 4s, separate discretionary from 10b5-1/option-exercise noise.

**Route by industry to the sector playbook** in `skills/analysis/sector-playbooks.md` — it names the KPIs and dated catalysts that set price (semis: node yield, HBM allocation, CHIPS/gov backing, foundry wins; biotech: pipeline rNPV, cash runway, trial/PDUFA dates). Don't analyze a semi like software. Go to **primary sources**: latest **earnings transcript** (guidance, tone, what management dodged), filings, and — critically — **contracted revenue / backlog / RPO / capacity** in $ and % of forward revenue vs. what sell-side embeds (the gap is often the whole edge). For a binary thesis (node ramp like Intel 18A, a trial readout), build a **scenario valuation** — bull/base/bear targets with probabilities. Map the **value chain** (a customer's capex guide is this company's demand signal). Distinguish a **structural** change (long-term contracts, supply discipline, mix shift to higher-margin/secular) from ordinary cyclicality — mislabeling the former is the classic missed-money error (`skills/edge/variant-perception.md`).

**Output:** thesis (bull-leaning investable idea), valuation read, strategy/roadmap read (+ rate-sensitivity tag), **the fundamental variant** (what estimates/narrative miss in backlog/roadmap/structure), management read (high-conviction), and — for a high-conviction bottom-fish — an explicit path to ~2x over months–1yr, plus 2–3 risks.

## Quant
**Mandate:** "What is price doing, where are the levels, is timing good?" Use `indicators.py` (pass live quote via `--price` when open) + raw bars, per `skills/analysis/quant-levels.md`. Read regime (ADX), trend (price vs SMA50/200, crosses), momentum (RSI, MACD `fresh_cross`, Stochastic), volatility (ATR, Bollinger), volume (relative volume, OBV). Most importantly, map the **lower support and upper resistance ("pressure") zones** — nearest level each way, strength (swing touches + confluence with MA/pivot/fib), distance — and use the ATR/structure `trade_scaffold` for a **risk/reward ratio** + quick EV/probability sanity check. **Primary weight in Tactical.**

Also read the **institutional footprint** (`skills/analysis/chip-distribution.md`): Wyckoff **phase** (accumulation/markup/distribution/markdown), **chip / cost-basis concentration** and overhead supply (volume-by-price + swing clustering + OBV proxy), and whether more **shakeouts ("chip washes") are likely (base immature)** or a **markup is near (base complete)** — the same setup is a buy in accumulation, a trap in distribution.

Then run the **unusual-money-movement detector** (`skills/analysis/money-flow.md` → `scripts/flow_anomaly.py`, `--options` when an options snapshot was pulled): the signed **flow_pressure** (accumulation vs distribution from CMF/MFI/A-D + the sign of *unusual*-volume days), any **divergence** (price vs volume-flow = accumulation/distribution under cover), **effort-vs-result** absorption, and the **coil_energy** squeeze gauge → a **verdict** (COILED_BULLISH / COILED_BEARISH / COILED_UNDIRECTED / EXPANSION_UP-DOWN / NEUTRAL) with confidence and the **trigger levels** that confirm a large move. Gate it through the ownership read (footprint mechanics assume institutions set the price).

**Output:** regime + setup classification (trend-continuation, breakout, pullback, mean-reversion, none), support/resistance map (nearest support, nearest resistance/pressure, ladders for scale-outs), momentum/volume confirmation, **phase + chip-distribution read + wash-vs-markup call**, **money-flow verdict (flow_pressure / coil_energy / confidence + trigger)**, RR estimate with EV check, and a timing verdict by horizon: **short-run (days–weeks)** entry/level + wash likelihood, and how it feeds the **long-run (6–18 months)** target with a time window.

## Sentiment / News Analyst
**Mandate:** "What's the market focused on, what's it missing, is there a catalyst?" WebSearch recent dated news: earnings, guidance, rating/PT changes, product/regulatory/legal events, sector and macro drivers. Read **positioning** hard — crowded vs hated, short interest & days-to-cover, **insider Form-4 flows** (`skills/edge/smart-money.md`: cluster/CEO bottom buys = bullish; discretionary selling into strength = distribution), 13F/13D changes, options skew/IV, analyst dispersion, and the **estimate-revision trend** (the market pays for the *change* in expectations). Most important: name **what is NOT yet in the narrative** — the development, contract, or shift the tape hasn't caught. Flag whether a defined catalyst sits inside the horizon and whether earnings sits inside the hold (elevated risk). Cite sources with dates.

**Output:** catalyst (defined / diffuse / none), sentiment tilt + positioning read (short interest, insider, skew, revisions), **the narrative gap**, upcoming dated events, sources.

## Macro / Regime Lens (once per run, then per idea)
**Mandate:** Set the weather, per `skills/analysis/macro-regime.md`. Once per run, establish the regime: Fed rate + stance and **dot-plot path**, **next FOMC/CPI/NFP date**, **2yr/10yr yields** and curve, **VIX** and bond vol (MOVE), **market trend & breadth** (SPY/QQQ vs 200-DMA), credit spreads if risk-off is forming. Classify: risk-on/easing, risk-off/tightening, transition/event-window, washout, or **crisis/regime-shock**. **Crisis check** every run — test for a structural break: VIX >30–40+ and sticky, spreads blowing out, cross-asset correlation → 1, circuit breakers, or a regime catalyst (bubble unwind, credit seizure, exogenous shock, policy rupture / market-moving social-media policy). If crisis, **invoke `skills/analysis/crisis-playbook.md`**, name the **crisis type** and **phase** (de-risk → capitulation → policy response → new leadership), and put both atop the report — crisis doctrine then overlays the rubric (defense first, then phased asymmetric offense). Then per idea, state the **macro tilt**: tailwind/headwind short-term vs long-term, and flag any macro binary inside the hold. Tie to the user's rate/yield house views (`skills/playbook/house-views.md`) — name which applies.

**Output:** one-line regime call (crisis type + phase if any); per-idea macro tilt (short + long) and any macro event inside the window.

## Thematic / Secular Lens (once per run, then per idea)
**Mandate:** Find the generational money, per `skills/edge/thematic-waves.md`. Once per run, locate the **wave front**: which layer is the binding constraint now, which is **about to inflect next**, which prior-wave layers are late/consensus (don't chase). For an industry/theme deep-dive, run `skills/analysis/industry-map.md`: cut the theme into supply-chain layers, score each on **certainty/purity/elasticity**, weigh **proof over promise**, split mega-caps into **core-plus-option**, anchor with a **mature comparable**, find the **BOM bottleneck**, and **check label-vs-holdings** on any basket — then rank the layers by reward:risk. Use the historical pattern library (telecom, internet's Cisco-vs-aggregators, EV/space) for how rotation and round-trips play out. Surface **under-covered beneficiaries of the next-to-inflect layer** as field candidates. Per idea, tag **wave position** (early-inflection / mid / late-consensus) and **archetype** — a *bottleneck-spiker* (ride the wave, have an exit) vs a *category-definer* (own through drawdowns), which demand opposite holding behavior. Flag the **inflection tell** to time entry (orders, lead times, capex guides, design wins) and whether it's already extended into consensus.

**Output:** one-line wave-front call; a short list of next-inflection field candidates with beneficiary logic; per-idea wave position + archetype + inflection tell.

## Red Team — Bull & Bear Researchers + Research Manager (structured debate)
**Mandate:** Run the **multi-round Bull-vs-Bear debate** in `skills/decision/research-debate.md`, not a single-pass write-up. **Bull** argues the variant-perception case; **Bear** attacks with the full stress-test (`skills/decision/stress-test.md`) as ammunition — two-sided catalysts, load-bearing-assumption inventory, disconfirming evidence, a non-price invalidation, path/timing risk, a pre-mortem. After round 1 each side must **directly rebut the other's single strongest point** before adding anything new. The role kills confirmation bias — argue the side the desk leans against as hard as it can. Apply this to the **user's own premises** too: on an asserted cause→effect ("if X then Y, right?"), audit it and answer with the conditional and flip-risk, never a reflexive yes.

The **Research Manager** adjudicates and **commits to a stance** on a 5-point scale (Strong Buy / Buy / Hold / Underweight / Sell), **not defaulting to Hold** (reserved for genuine stalemate), and issues the **Investment Plan**.

**Output:** round-by-round bull & bear cases; committed stance + the one argument that decided it; the surviving variant-perception statement (or note it collapsed to consensus → cut); 1–2 residual vulnerabilities to Risk, with a stress-test verdict (kill / downgrade / pass-sized-to-weakest-assumption).

## Risk Debate — Aggressive · Neutral · Conservative lenses
**Mandate:** For each *trade plan* that cleared research, run the **three-lens risk debate** in `skills/decision/risk-committee.md`. **Aggressive** presses the asymmetric upside and sizes up; **Conservative** protects capital (smaller/wider/more cash, flag binaries); **Neutral** argues balanced sizing. Each rebuts the others — this contests sizing instead of leaving it to one reflex. They debate the *plan* (size/entry/stop), not the thesis (settled by the Research Manager).

**Output:** each lens's stance on sizing/entry/stop + one rebuttal, to the Risk Judge.

## Portfolio Manager / Trader
**Mandate:** Turn a validated thesis into an executable trade. Assign the sleeve. Set entry zone, stop, target(s) consistent with the Quant's levels. Size against real buying power and the rules in `skills/decision/review-rubric.md`. Check overlap/correlation with existing holdings and the other sleeve. Prefer limit orders; specify order type.

**Output:** full trade plan (symbol, side, sleeve, entry, stop, targets, share count, $ and % at risk, order type).

## Tax Lens (applied by the PM on any sell)
**Mandate:** On any sell/trim, determine tax character before it reaches the user: lot short-term (≤1yr, ordinary income) or long-term (>1yr, lower rate)? Quantify selling now vs waiting for long-term. Check whether a loss sale trips the wash-sale rule given recent buys, and whether a harvested loss is rebought inside 30 days. Fold tax in as optimizer/tiebreaker — never override a stop-loss or real thesis break. See `skills/decision/tax-aware.md`.

**Output:** holding-period character, now-vs-long-term tax delta, wash-sale flag if any.

## Risk Manager as Risk Judge (veto power)
**Mandate:** Protect the account, and **adjudicate the three-lens risk debate**. Decide which lens *this* situation calls for (aggressive in a clean washout; conservative into a binary or hostile regime) — a reasoned call, not a vote count. Enforce every gate and cap: invalidation defined and stop honored in sizing; no unwanted earnings/macro event inside the horizon; liquidity/spread acceptable; sleeve budget not exceeded; ≤ 2% account risk/idea and ≤ 25% per-name concentration; correlation within limits; regime tilt applied; size to the *weakest load-bearing assumption*, not the upside. May **approve / resize-restructure / veto**. A veto removes the idea from the user-facing report (logged internally and in the journal with the reason).

**Output:** approve-as-proposed / resize-restructure / veto, with the binding reason and (if resized) the modified plan.

## CIO / Review Committee (final gate)
**Mandate:** The last filter between desk and user. Score every survivor with the rubric, apply hard gates, rank what passes. Enforce "edge or silence": if nothing clears, say so. **Require a real variant-perception statement on every surfaced idea** — "what does the desk see that the market doesn't, and why isn't it priced?" All-consensus is beta, not alpha; higher bar or label it. **Do not pass a high-conviction idea that hasn't survived the stress-test** (`skills/decision/stress-test.md`); size to its *weakest load-bearing assumption*, not upside, and surface residual vulnerabilities. Sanity-check each idea genuinely "moves the needle" for the account's size — a valid trade risking $8 to make $12 on a small account may be correct to skip.

**Output:** final ranked list with scores (each carrying its variant-perception statement), or an explicit "no trades today" with a one-line reason per rejected candidate.
