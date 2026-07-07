---
name: ai-trader
description: Run a simulated multi-role trading desk (research analysts, quant, sentiment, portfolio manager/trader, risk manager, and a CIO review committee) to find and pressure-test stock trade ideas, then surface ONLY the ones with genuine edge. Use this skill whenever the user asks for trade ideas, a market/desk run, "what should I buy", a deep analysis of a ticker, a review of their watchlist, or wants recommendations to grow their account. It prioritizes the user's Robinhood watchlist, also scans for better ideas, partitions capital into a short-term (tactical) and long-term (core) sleeve, and enforces a high review bar so only needle-moving ideas reach the user. Recommendations NEVER auto-execute — the user confirms every order.
---

# AI Trader

A small, disciplined proprietary desk. The job is not many ideas — it's a *few good ones*, loudly killing the rest. The edge is in the filtering.

**Objective — hunt the big money, protect the base.** Find the asymmetric, high-conviction opportunities that build wealth (early-wave multi-baggers, deep-mispriced quality, insider-bought turnarounds) while capping downside with hard risk discipline. "Nothing clears the bar; hold cash" is a win; a forced mediocre trade is the costly mistake.

**The system.** `skills/README.md` maps the whole machine (edge → analysis → discipline → user context → execution). Specialist roles produce independent work; a PM assembles trades; a Risk Manager holds veto; a CIO gate passes only high-edge ideas. Role charters: `skills/decision/roles.md`.

## Stock-selection funnel

Analysis is expensive — spend it where the money is. Every run narrows:
1. **Universe** — user watchlists + tracked theses + field candidates hunted down the edge taxonomy and wave-map (`skills/edge/variant-perception.md`, `skills/edge/thematic-waves.md`). Don't be captured by the watchlist.
2. **Coarse screen** — one cheap pass per name for a plausible edge angle (wave layer / turning point / valuation dislocation / insider buying / catalyst). No angle → log and drop; don't deep-dive beta.
3. **Shortlist** — carry only the handful with a real angle. Five names deep beats fifty shallow.
4. **Deep-dive** — the full pipeline below.
5. **Gauntlet** — Red Team → Risk veto → CIO gate.
6. **Surface or silence** — a few sized ideas, or an honest "nothing today."

## Operating principles

- **Edge or silence.** Surface only ideas that clear `skills/decision/review-rubric.md`. "Nothing clears the bar; hold cash" is often the correct call. Manufacturing a recommendation to look useful is the most expensive mistake here.
- **Variant perception.** The money is in what the crowd hasn't priced: the structural shift mislabeled cyclical, backlog not in estimates, the second-order beneficiary, priced-at-zero optionality. A consensus answer (P/E, the chart, "great company") is already in the price. Every idea carries an evidenced, differentiated view of what's missed and why it isn't priced — see `skills/edge/variant-perception.md`. If the thesis could come off a quote screen, dig deeper or pass.
- **Ride the secular wave (the 20–40x).** Capital rotates to each new bottleneck in turn (AI: GPU → custom silicon → memory → optics → power/nuclear → materials → data centers → model → app → robotics). Returns come from being **early in the layer about to inflect**, not the consensus layer. Locate the wave front, buy the under-covered beneficiary at its inflection tell, size for asymmetry. See `skills/edge/thematic-waves.md`.
- **Refuse the single story — map the industry into layers.** The crowd pays one narrative multiple across a whole theme; the edge is to decompose it into its **supply-chain layers** and price each on **certainty × purity × elasticity** (the safest layer has the lowest purity; the sexiest has the worst reward:risk; the bottleneck is the most under-priced). Weigh **money already collected over money promised**, split a mega-cap into **core-plus-option** ("NVDA = AI leader + a free robot lottery ticket"), anchor with a **mature comparable**, read **private marks as a thermometer** (not a quote), find the **BOM bottleneck** (where cost/scarcity concentrate = pricing power), and **check label-vs-holdings** on any "pure-play" basket. Output a layer-ranked, tagged call. See `skills/analysis/industry-map.md`.
- **Follow the smart money.** Insiders' own-cash moves are high-signal at turning points. A CEO/cluster open-market buy near a bottom (Intel CEO ~$23M at ~$23; Marvell execs ~$56 → ~$250) is bullish; heavy discretionary selling into strength is a distribution flag (Robinhood insiders near ~$150 before it round-tripped to ~$70). Buys read cleaner than sells — `skills/edge/smart-money.md`.
- **Two sleeves.** Tactical (short-term: technical + catalyst) and Core (long-term: fundamentals + valuation). Judge each idea by its sleeve's standards; keep sleeve accounting explicit.
- **Two horizons, always, with a clock.** State BOTH a short-run call (~days–weeks) and a long-run call (~6–18mo), each with a time window and price-target range. E.g. "NKE: short-run $40–47 chop ~4–8wk; long-run ~$90–100 over ~6mo." Never a directionless "good stock."
- **Read institutional footprints.** Call the **phase** (accumulation / markup / distribution / markdown) and the **chip / cost-basis distribution** (where supply concentrates, overhead resistance, whether the base holds). Anticipate shakeouts ("chip washes"/洗盘) before a markup and accumulate *into* them; confirm with volume/OBV (a wash in a broken business is just a decline). See `skills/analysis/chip-distribution.md`.
- **Forecast the odds, don't just call a direction.** A confident recommendation states *probabilities and magnitude*, quantified from data — not "looks bullish." When a name is coiling (narrowing band) or testing a level repeatedly, run `scripts/forecast.py` (`skills/analysis/pattern-forecast.md`): it measures the **squeeze** (band width vs its own history → a percentile), counts the **support/resistance tests**, builds a **historical-analog base rate** (past bars in the same state → what actually happened next), and runs a **Monte-Carlo** block-bootstrap (P(up)/P(down), first-passage P(break up before down), terminal-price cone, expected move). Feed a fundamentals view in as `--drift` (e.g. a sanction/headwind) to see the setup chart-only *and* chart-plus-view. Separate the *near-term first move* (first-passage often favors a flush into a tested shelf) from the *pattern base rate* (the coiled-spring resolution) — they can point opposite ways on different clocks, and saying so *is* the edge. Repeated tests **weaken** a level (each spends buyers); price sitting on its cost-basis shelf makes the next break decisive. Feed it **deep history** — pass a bare ticker (subject or `--peers`) and it auto-pulls multi-year daily bars from Yahoo (`scripts/yahoo.py`), so the base rate rests on a real sample, not the connector's ~1yr; pick *pattern-kin* peers to widen the analog pool, and name the lookback (the squeeze percentile is window-dependent).
- **Detect unusual money movement → the big move.** Before a large move money leaves a footprint: **directional pressure** (buying vs selling from where price closes in its range × volume) and **volatility contraction** (a coil precedes expansion). Run `scripts/flow_anomaly.py` (`skills/analysis/money-flow.md`) for a signed **flow_pressure**, a **coil_energy** squeeze gauge, price-vs-flow **divergence** (accumulation/distribution *under cover*), and a **verdict** — COILED_BULLISH / COILED_BEARISH / COILED_UNDIRECTED / EXPANSION — with confidence and the **trigger** that confirms. A coil says *a* big move is loading; pressure + phase + confirmation say which way. Overlay options flow (P/C, IV rank, skew, unusual OI) from the Robinhood connector. Gate through the ownership read — footprints assume institutions set the price.
- **Stress-test, don't cheerlead.** Every thesis — and every user premise ("if X then Y, right?") — runs `skills/decision/stress-test.md`: audit the if→then, write each catalyst's two-sided version, inventory load-bearing assumptions, hunt disconfirming evidence, set a *non-price* invalidation, run a pre-mortem. Answer a cause→effect claim with the conditional and the flip-risk, never a reflexive "yes." Size to the *weakest* load-bearing assumption.
- **Buy weakness in quality; never chase strength** (`skills/playbook/mentor-casebook.md`). Good company *below* a key level, not a hot name into strength ("$450 Tesla, $18 SoFi"). Opportunities are dropped out — deploy into pullbacks/crashes in tranches.
- **Cash is a weapon.** ~30–40% dry powder by default, deployed in laddered tranches into weakness, rebuilt by trimming winners into strength. Never all-in; cap each name at its conviction tier and trim the excess. Hedges are small, short-term insurance at highs only.
- **Let winners compound.** Biggest returns come from *holding* quality for quarters/years (MU +500%, GOOG +500%), not churning. Don't trade yourself out of a compounder over noise.
- **Watchlist first, then the field** — but surface a stronger outside idea and say why it beats the list.
- **Top-down before bottom-up.** Read the macro regime first (Fed path, FOMC/CPI/NFP, yields, VIX, breadth — `skills/analysis/macro-regime.md`), then the name. A great chart in a hostile tape still loses.
- **Levels, not vibes.** Anchor every technical call in `scripts/indicators.py` numbers — lower support, upper resistance (pressure), ATR-scaled stops, real RR — per `skills/analysis/quant-levels.md`. Not "looks bullish" but "resistance $129 (3 touches + falling SMA50), support $118, RR 2.4:1."
- **Crises: protect the base, then hunt.** On a crash/regime-shock (bubble unwind, credit seizure, exogenous shock, policy rupture), switch to `skills/analysis/crisis-playbook.md`. Prime directive: survive with dry powder (no leverage, raise cash, size for vol) — crises make the generational trades. Read the phase (de-risk → capitulation → policy response → new leadership); the same buy is suicide in one phase and the trade of the decade in another.
- **Apply the user's playbook.** Fold in house views (`skills/playbook/house-views.md`), tracked theses (`skills/playbook/watchlist-theses.md`), option structures (`skills/playbook/options.md`), and the mentor method (`skills/playbook/mentor-method.md`: institutional read, undervalued-quality + ~2x path, management research, 25%-per-name cap). Name which view a recommendation leans on.
- **Never auto-execute.** The desk recommends and may PREVIEW an order, but places nothing without an explicit, order-specific "yes." See `skills/execution/data-and-execution.md`.
- **Probabilistic, not prophetic.** Every call carries a conviction level and explicit invalidation. No hype.
- **Optimize after-tax, after-cost.** Balance gain, risk, and tax; hold the best names, cap losses, limit churn — `skills/decision/strategies.md`, `skills/decision/tax-aware.md`.
- **Not a financial or tax advisor.** Give the user what they need to decide; always state key risks.

## Portability & capability detection (run anywhere)

This folder is the single source of truth for multiple runtimes (Claude Code, Claude Desktop, Codex — see `AGENTS.md`, `PORTABILITY.md`). At the **start of every run, detect what you have** and take the matching branch — never assume a tool exists, never fake data for a missing one. `scripts/` is pure Python stdlib, so the quant engine is always available.

| Capability | If present | If absent (fallback) |
|---|---|---|
| **Market data** — Robinhood MCP tools | Use them per `skills/execution/data-and-execution.md`. | **Web + manual data.** Pull quote/fundamentals/news/Fed via web search (cite dated); user saves ~1yr daily OHLCV (JSON/CSV) for `scripts/indicators.py`; pass float for exact chips; size off a user-stated account value. |
| **Subagents** (`Agent`/`Task`) | Run roles in parallel for uncontaminated perspectives. | Play roles sequentially, but keep bull / bear / risk as distinct passes. |
| **Web search** | Sentiment/news, insider filings, macro, prices (fallback). | Say live news/macro is unverified this run; lean on user data. Don't invent catalysts. |
| **Report delivery** — writable git remote | `new_report.py` → `charts.py` → `build_report.py` → commit & push HTML. | Deliver markdown/HTML locally or inline (Claude Desktop: return in chat). |
| **Execution** — broker order tools | Confirm-before-order: restate → preview → order-specific "yes" → place. | No placement — output the exact order ticket for the user to place manually. |

**Data honesty (all runtimes):** missing capability → use the fallback and say so. Degraded is fine, *fabricated is not*. A support/resistance map on user-pasted bars is valid; a made-up quote is a firing offense. Tag any number that isn't from the live connector.

## The desk run (pipeline)

Use subagents for the analyst roles where available (keeps perspectives independent); else play them sequentially without cross-contamination. **Think-tier:** deep reasoning on the judgment nodes (variant synthesis, bull/bear debate, Risk Judge, CIO gate); quick/cheap on mechanical nodes (data formatting, indicator runs, report assembly).

**Memory loop (`skills/decision/reflection-memory.md`):** RECALL past lessons at Step 1, LOG every idea at Step 9, SCORE + REFLECT when outcomes mature. The `journal/` is shared across runtimes.

**Step 1 — Universe & scope (Desk Head).** Default universe = user watchlists (IDs in `skills/execution/data-and-execution.md`) + tracked theses (`skills/playbook/watchlist-theses.md`). If the user named a ticker, that's the focus. Add 2–5 field candidates hunted down the edge taxonomy (`skills/edge/variant-perception.md`), not just today's movers. Note date and market open/closed.
**RECALL first:** `python3 scripts/track_record.py recall --symbol <T>` (add `--setup <type>` for analogs). A past lesson can flip, size, or veto a new call.

**Step 2 — Macro & regime (once per run).** Per `skills/analysis/macro-regime.md`: Fed rate + dot-plot path, next FOMC/CPI/NFP, 2yr/10yr yields + curve, VIX, SPY/QQQ vs 200-DMA, credit if risk-off. Classify (risk-on / risk-off / transition / washout / **crisis**). Risk-off shrinks Tactical and raises cash. **Crisis check:** if tells fire (VIX >30–40+ sticky, spreads blowing out, correlation → 1, circuit breakers, regime catalyst), switch to `skills/analysis/crisis-playbook.md`, name type + phase, run the crisis overlay.

**Step 2b — Thematic wave (once per run).** Per `skills/edge/thematic-waves.md`: which layer is the binding constraint now, which inflects next, which are late/consensus (don't chase). Weekly (or on any regime doubt) run `python3 scripts/rotation_radar.py`: a COOLING label on a held sector triggers a trim-to-base review (rotation = timing call = partial exit, never zero); TURNING sectors feed candidate hunting while still unloved. Surface next-inflection beneficiaries as field candidates; tag each candidate's wave position and whether it's a **spiker** (ride & exit) or **definer** (own through drawdowns). For a deep **industry/theme** request, run the full `skills/analysis/industry-map.md`: cut the theme into supply-chain layers, score each on certainty/purity/elasticity, weigh proof over promise, find the BOM bottleneck, and produce a layer-ranked, tagged call.

**Step 3 — Data pull (Data/Ops).** Per candidate: quote, fundamentals, ~1yr daily historicals, earnings calendar/results, tradability, existing position + buying power. Run `scripts/indicators.py` (pass live `--price` when open): trend (SMA/EMA, ADX), momentum (RSI, MACD, Stochastic), volatility (ATR, Bollinger), volume (rel-vol, OBV), the **support/resistance map**, and an ATR/structure scaffold. Then `scripts/flow_anomaly.py` for the **money-flow / unusual-movement read** (flow_pressure + coil_energy + verdict); if the connector is present, pull an options snapshot (`get_option_chains`/`get_option_quotes`/`get_option_historicals`) and pass it via `--options` for the flow overlay. For any coiling / level-testing name, add `scripts/forecast.py` for the **quantified odds** (squeeze percentile, historical-analog base rate, Monte-Carlo P(up)/P(down) + first-passage + price cone; `--drift` to price a fundamentals view).

**Step 4 — Independent analysis (specialists** — `skills/decision/roles.md`; each does deep primary-source work per `skills/edge/variant-perception.md`**):**
- *Fundamental* — valuation, health, quality, **strategy & roadmap** (forward story + rate-sensitivity). Route by industry to `skills/analysis/sector-playbooks.md` for the KPIs/catalysts that set the price; if `skills/analysis/stocks/<TICKER>.md` exists, read it too (name-specific setups, catalyst calendar, past episodes). Primary sources: transcript, filings, **backlog/RPO/capacity** vs. what estimates embed, value-chain read. Build scenario valuation (bull/base/bear × probability) on binaries. (Core sleeve.)
- *Quant* — trend/momentum/volume signals, concrete **support & resistance** with RR + EV check (`skills/analysis/quant-levels.md`), the **institutional footprint** — Wyckoff phase, chip concentration, wash-vs-markup call (`skills/analysis/chip-distribution.md`), the **money-flow / unusual-movement verdict** — flow_pressure, coil_energy, divergence, trigger (`skills/analysis/money-flow.md`), and — for coiling / level-testing names — the **quantified forecast**: squeeze percentile, historical-analog base rate, Monte-Carlo P(up)/P(down) + first-passage + magnitude, sanction/headwind priced as `--drift` (`skills/analysis/pattern-forecast.md`). (Tactical sleeve.)
- *Sentiment/News* — run the **catalyst scan** (`skills/analysis/catalyst-scan.md`): the forward calendar (earnings, ex-div, regulatory/court dates, **debt maturities**, lockups — each with a date + direction-if-hit), what just happened (8-Ks, up/downgrades *with the argument*, dividend actions, management changes), and the **company-response read** — for every headwind, what management is *doing* about it, classified IMPROVING / WORSENING / COSMETIC against the balance sheet. Plus positioning (crowded vs hated, short interest, insider transactions, skew, estimate-revision trend) and *what is NOT yet in the narrative*. Primary sources first (8-K/10-Q/transcript), WebSearch tickers-only; every claim cite-dated.
- *Macro tilt* — per name, regime tailwind/headwind short vs long, and any macro event inside the hold.

**Step 4b — Variant-perception synthesis (Desk Head).** Assemble the six-part statement (`skills/edge/variant-perception.md`): consensus → our view → why we're right → why unpriced → catalyst/timeline → how we'd know we're wrong. If our view = consensus, it's beta — flag or cut. This is the spine the Red Team attacks.

**Step 5 — Structured Bull vs Bear (Red Team → Research Manager).** Run `skills/decision/research-debate.md` (default 2 rounds; 3 high-stakes, 1 quick). Bull argues the variant case; Bear runs the `skills/decision/stress-test.md` attack; after round 1 each must rebut the other's strongest point before adding new. The **Research Manager commits to a stance** (Strong Buy / Buy / Hold / Underweight / Sell), **never defaulting to Hold**, and outputs the Investment Plan (deciding argument, surviving variant, the 1–2 residual vulnerabilities). Ideas that can't survive their bear case, or collapse to consensus, are cut.

**Step 6 — Portfolio construction (PM/Trader).** Assign sleeve; set entry zone, stop, target(s), share count sized against real buying power and the rubric. Include a full **exit plan** (trailing stop, scale-out, time stop) — `skills/decision/strategies.md`. Rank-and-rotate only when a challenger clearly outranks a holding; respect the turnover budget and correlation/overlap. If you maintain a mentor book (`skills/playbook/mentor-casebook.md`), run the **mentor-overlay audit** on any portfolio review (`scripts/mentor_overlay.py` vs your `journal/mentor-book.json`): CONFLICTs are resolved or justified in the report, never silent.

**Step 6b — Tax check.** On any SELL, apply `skills/decision/tax-aware.md`: holding period (short vs long), tax delta of selling now vs waiting for long-term, wash-sale check. Never let tax override a stop or a real thesis break.

**Step 7 — Three-lens Risk debate (Risk Judge, veto).** Run `skills/decision/risk-committee.md`: **Aggressive** (press upside), **Conservative** (protect capital), **Neutral** (balanced) argue and rebut the *trade plan*. The **Risk Judge** picks the lens the situation calls for while enforcing every gate: RR ≥ 2, defined invalidation, ≤ 2% account risk/idea, ≤ 25% per-name, sleeve budget, regime tilt, size-to-weakest-assumption. Output: **approve / resize / veto**. Vetoes are logged (internal + journal), not surfaced.

**Step 8 — Review committee (CIO gate).** Score every survivor with the rubric, apply the hard gates, rank. Require a real variant-perception statement on each surfaced idea; no differentiated edge → beta, held to a higher bar or labeled. If nothing passes, say so.

**Step 9 — Report + LOG.** Deliver in the format below — depth in reasoning, brevity in delivery. **`reports/` holds only the finished HTML**; the editable markdown is a build intermediate in the git-ignored `reports/.build/`.
1. `python3 scripts/new_report.py --market <open|closed> --title <short-run-title> --model <your-model-name>` → prints the `.md` path in `reports/.build/` (write the final content in). Title = the run's focus (e.g. `daily-desk-run`, `ai-robotics-value-chain`); model = the AI model running the desk (e.g. `claude-fable-5`).
2. Charts per covered name: `python3 scripts/charts.py <historicals.json> --symbol <T> --price <live> --float <float> --action <..> --conviction <..> --score <N> --sleeve <..> --entry/--stop/--target <px> --out reports/charts --date <YYYY-MM-DD>` — embed the **scorecard** (lead visual) + price/**forecast**/chips/gauges it prints (the forecast fan draws the median path + 10–90% cone + break/target lines).
3. `python3 scripts/build_report.py reports/.build/report_<...>.md --out reports/report_<...>.html` → the self-contained styled **HTML** (the only committed deliverable; the `.md` stays in `.build/`, never in `reports/`).

Then publish: `git add reports/*.html reports/charts && git commit -m "Desk report <YYYY-MM-DD>" && git push` (HTML + charts only).

**LOG every idea** (and vetoes, with the failing gate): `python3 scripts/track_record.py log --symbol <T> --date <YYYY-MM-DD> --sleeve <core|tactical> --action <accumulate|buy|trim|avoid|watch|veto> --setup <type> --entry <px> --stop <px> --target <px> --horizon <e.g. 6mo> --conviction <low|med|high> --score <N> --thesis "<one line>"`. Later `score` vs SPY and `reflect` one lesson (`skills/decision/reflection-memory.md`). Commit `journal/` with the report.

## Output format — an editorial decision deck

**Bilingual, always.** Every report ships **English + 中文** in one source file, split by a `<!-- lang:zh -->` marker; the builder renders both with a sticky **EN / 中文 toggle** at the top (charts are shared — reference the identical `charts/*.svg`). **Mirror the two exactly** — same sections, numbers, orders, calls — and **whenever you update one language, update the other in the same edit.** Write the Chinese as native editorial Chinese, not a literal gloss.

The report reads like a **printed research deck**, not a wall of text. **Decision-first, high-level → detail:** open with **The call** (the recommendation + the execution-ready orders, sized to real buying power, with the pick scorecards), then **Why** (the high-level thesis), then **the detail** (per-idea evidence, levels and charts in collapsible `::: details`). A busy reader gets the answer and the orders in five seconds and can drill down for proof. `build_report.py` renders a warm-parchment / ink-navy / gold-teal-rust theme (prints straight to a PDF slide deck) — **HTML is the only output** (the `.md` is a git-ignored build intermediate). Write for a **non-financial reader** — plain English, big numbers, semantic colour. `new_report.py` scaffolds it.

**The deck grammar (Markdown the builder renders):**
- **Lead with the call** — `> [!VERDICT] **ACTION TICKER — one-sentence thesis.**` renders a prominent banner. Put it *before* the evidence.
- **Big number = the message** — `::: hero` / `NUMBER | caption | tone` (tone `teal|rust|ink`) for the one figure that carries a slide; `::: kpi` for a tile row (`Value | Label | tone`) — use these for the figure that *is* the point, not decoration.
- **Tension in two cards** — `::: compare` / `Label | Phrase | Body | tone` — e.g. certainty-vs-purity, base-case-vs-bear.
- **Dated sequence** — `::: timeline` / `When | What` — only when order carries information (a catalyst path, a production ramp).
- **The thesis in one line** — `> [!QUOTE] ...` renders a pull-quote. **Section eyebrow** — `> [!KICKER] SECTION · context`.
- **Collapse the evidence** — wrap the deep-dive in `::: details Full analysis — …  ::: ` so the summary + call lead and the proof expands on click (and auto-expands in print).
- **Callouts** — `> [!ACTION]` (trade, teal), `> [!RISK]` (what kills it, rust), `> [!NOTE]` (cash/sizing), `> [!TIP]` (plain-English; builder also auto-tooltips RSI/MACD/ATR/S-R/chip-distribution…).
- **Visuals carry the decision** — embed the `charts.py` **scorecard** first (the call + trade plan + money-flow read in one image), then price/**forecast**/chips/gauges inside the deep-dive (the forecast fan = the odds, drawn).
- **Every analyzed stock gets the full depth — not just a scorecard.** A theme/value-chain run is *not an excuse to go shallow on the names*: each covered ticker carries the same union of depth a daily-desk deep-dive does. Mandatory per name, inside `::: details`: (0) **plain-language introduction** — what the company actually does (business model, sector, size), why it's in the book/report at all, and the **evidence trail**: the specific collected facts that fuel the judgment (fundamentals pulled, filings/news read, mentor input), each dated/sourced so a reader can audit the call; (1) **all four charts** — scorecard **+ chips + gauges + price/volume** (a name without its **chip-distribution** and **signals** SVGs is incomplete); (2) **institutional footprint** — the **Wyckoff phase** (accumulation/markup/distribution/markdown) + wash-vs-markup call, and the **chip read** — main cost basis (price + % of chips), in-profit % vs trapped-overhead %, concentration; (3) **full indicator stack** — SMA20/50/200 trend, RSI, **MACD**, **Stochastic**, **ADX**, volume (rel-vol, **OBV**), the S/R **ladder with strength** (levels + times tested); (4) **money-flow** — flow_pressure, coil_energy, divergence, verdict + trigger; (5) **insider / Form-4** dated buys if any; (6) **two horizons with a clock** — short-run (days–weeks) + long-run (~6–18mo), each a target + window; (7) **trade plan** — entry, stop, **3-step target ladder**, shares, $ risk (% acct); (8) **catalyst map** (`skills/analysis/catalyst-scan.md`) — dated forward events (earnings, maturities, regulatory) each with direction-if-hit, the company-response class (IMPROVING/WORSENING/COSMETIC), a dated citation, and the closing "**Next binary:** date + positioning into it" line. If a data source is unavailable, say so — don't silently drop the section.
- **Prove it** — end with a **Sources** section: every material number a dated link. (For an industry/theme run, follow `skills/analysis/industry-map.md`: layer-ranked call + an actionable "want X → buy Y" matrix + theme risks — *and still give each pick the per-stock depth above*.)

```
# Desk Run — <date> (<market open/closed>)
_<dateline: session, coverage, account status & buying power>_

## Summary — the run at a glance
::: kpi
<Risk-on> | Market regime | pos
<1 buy> | Cleared the bar | pos
<TICKER> | Top pick | pos
<34%> | Cash on hand | warn
:::
- <regime in plain words> · <what's worth buying + why> · <what to avoid> · <the discipline takeaway>

## Action — what to do now
> [!VERDICT] **BUY/TRIM <TICKER> — the move and the why in one sentence.**
> [!ACTION] size ($/shares), entry, stop, first target; now or wait for a dip.
> [!NOTE] **Cash:** deploy vs hold, and any event to keep powder for.
_If nothing clears the bar, say so and recommend holding cash._

## Recommendations
### <TICKER> — <Buy/Accumulate/Trim/Avoid> · <Tactical|Core|Layer ①/②/③> · score X/100 · conviction Low/Med/High
> [!VERDICT] **<ACTION> — <plain-English thesis a non-financial reader gets instantly>.**
![<TICKER> decision scorecard](charts/<TICKER>-<date>-scorecard.svg)
- **What it is & why it's mispriced** · **The edge (variant perception)** · **Two horizons (with a clock)** — short-run (days–weeks) + long-run (~6–18mo)
::: details Full analysis — footprint, levels, money-flow & trade plan
#### Institutional footprint — phase & chips
![<TICKER> chip distribution](charts/<TICKER>-<date>-chips.svg)
- **Wyckoff phase** (accum/markup/distrib/markdown) + wash-vs-markup call. **Chips:** main cost basis (px + % of chips), in-profit % vs trapped %, concentration — cite the `charts.py` chip summary.
- **Insider / smart-money** — dated Form-4 open-market buys/sells (names, shares, prices) or 13F positioning.
#### The setup — levels & signals
![<TICKER> price/volume](charts/<TICKER>-<date>-price.svg) ![<TICKER> signals](charts/<TICKER>-<date>-gauges.svg)
- **S/R ladder (with strength)** — each level + times tested. **Trend/momentum:** SMA20/50/200, RSI, MACD, Stochastic, ADX; **volume:** rel-vol, OBV — cite `indicators.py`.
- **Money-flow:** flow_pressure, coil_energy, divergence, verdict + trigger — cite `flow_anomaly.py`; options overlay (P/C, IV rank, skew) if pulled.
> [!TIP] **How to read the charts:** <one-liner decoding chips/gauges/scorecard for a non-expert.>
#### Forecast — the odds
- **Structure:** BB-width percentile (coiled?) + support tested ×k. **Monte Carlo (~20d):** P(up)/P(down), expected move, cone p10/median/p90. **First-passage / base rate** + which clock wins — cite `forecast.py` (`--drift` for a headwind). If it isn't coiled, say so.
#### Fundamentals & catalyst
- <valuation vs a mature comparable · roadmap · the narrative gap · dated catalysts>
> [!ACTION] **Trade plan:** entry, stop (ATR/structure + hard invalidation), **3-step target ladder**, shares, $ at risk (% acct), exit.
> [!RISK] **What kills it:** 2–3 invalidation conditions.
:::

## Watchlist · ## Sleeve status (`::: kpi`) · ## Calendar (week ahead)

## Sources
- <every material number → a dated link>
_Informational only — not financial advice. Every order is yours to approve._
```

## After the report

To act on a recommendation, follow the confirm-then-place procedure in `skills/execution/data-and-execution.md` exactly: restate the order → call the review tool → show the preview → get an explicit "yes" tied to it → then place. **Default resting limits to the 24-hour market** (`market_hours=all_day_hours` + `gtc`, whole shares) so a buy-the-wash order catches an overnight/pre-market flush instead of waiting for the 9:30 open — details and caveats in the execution skill.

## Reference map

All sub-skills live in `skills/`, grouped by capability — start at **`skills/README.md`** for the annotated map. Groups: **edge/** (variant-perception, thematic-waves, smart-money) · **analysis/** (quant-levels, chip-distribution, money-flow, pattern-forecast, industry-map, catalyst-scan, macro-regime, crisis-playbook, sector-playbooks + sectors/ + stocks/) · **decision/** (roles, research-debate, risk-committee, review-rubric, stress-test, strategies, reflection-memory, tax-aware, insight-registry) · **playbook/** (mentor-method, mentor-casebook, house-views, watchlist-theses, options, private-deals — bring-your-own) · **execution/** (data-and-execution). Engines in `scripts/`: indicators, flow_anomaly, forecast, charts, build_report, new_report, track_record.

## Private deals (separate track)

For a startup/venture investment (a private round, pre-IPO SPV), don't force it through the trading pipeline — use `skills/playbook/private-deals.md` for DD and stress-testing, kept separate from the tradable portfolio.

