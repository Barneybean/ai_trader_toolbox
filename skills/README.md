# Skills map — the desk operating system

**Objective:** find the asymmetric, big-money opportunities (early-wave multi-baggers, deep-mispriced
quality) while protecting capital with hard risk discipline — be *early and right* on the moves that
matter, and say "nothing today" the rest of the time.

The ordered run lives in `../SKILL.md`. This file maps the sub-skills: what each is for and how they
layer. Sub-skills are grouped by capability under `skills/`.

## Process (root)
- `../SKILL.md` — the end-to-end run (funnel → pipeline → report) + the portability/capability-detection fallback map.
- `../AGENTS.md` — portable entry point for Codex / any AGENTS.md agent; points back to `SKILL.md`.
- `../PORTABILITY.md` — how one source folder mirrors to every runtime.

## edge/ — where the money is (thesis engine)
- `edge/variant-perception.md` — the core edge: find what isn't priced; the required variant statement, edge taxonomy, deep-research playbook.
- `edge/thematic-waves.md` — secular-wave / capital-rotation lens; the AI wave-map; how to find/time/size the multi-bagger.
- `edge/smart-money.md` — insider Form-4 & institutional flows as weighted evidence (buys at bottoms vs. selling into strength).
- `edge/channel-mining.md` — followed-channel transcripts as evidence: a local [YouTube Transcriber](https://github.com/Barneybean/youtube-transcriber) service + `../scripts/ops/transcribe_channel.py` build a transcript library, and the distillation protocol (conflict review → insight-registry hypotheses) turns them into lenses. Underwrite, never chase.

## analysis/ — how to analyze a name
- `analysis/quant-levels.md` — the level engine: support/resistance map, ADX, momentum, ATR stops, RR/EV (drives `../scripts/analysis/indicators.py`).
- `analysis/chip-distribution.md` — institutional footprint: Wyckoff phase, chip/cost-basis distribution, accumulation vs. distribution, anticipating chip washes (洗盘).
- `analysis/money-flow.md` — unusual-money-movement detector: signed flow pressure (CMF/MFI/A-D + unusual-volume sign), price-vs-flow divergence, effort-vs-result absorption, the squeeze/coil energy gauge, options overlay → a COILED_BULLISH/BEARISH/EXPANSION verdict + trigger (drives `../scripts/analysis/flow_anomaly.py`).
- `analysis/industry-map.md` — layer a theme into its supply chain; score each layer on certainty/purity/elasticity; proof-over-promise, core-vs-option, mature-comparable yardstick, BOM bottleneck, label-vs-holdings → a layer-ranked, tagged call. The method behind an industry/theme deep-dive.
- `analysis/business-inflection.md` — mandatory forward-business read for single-name deep dives: inventory strategic changes, map them to estimates versus multiple reclassification, decide what is priced, and attach a dated proof clock.
- `analysis/valuation-quality-gate.md` — executable fundamental hard gate: business quality and survivability plus the expectations already embedded in price; exemptions must be explicit.
- `analysis/value-radar.md` — the ≥30% undervaluation hunt: fair value = median of ≥2 independent legs (owner-earnings DCF at underwritten growth, mature-comparable multiple, own-history band — `../scripts/analysis/value_radar.py`), washed+basing entry gate (cheap-and-knifing = WAIT + an action level), survivable bear floor, and the funnel (TURNING sectors, washouts, insider clusters, overreactions). The radar ranks; the quality gate, catalyst map and gauntlet decide.
- `analysis/catalyst-scan.md` — dated-event radar: the forward calendar (earnings, maturities, regulatory — each date + direction-if-hit), why-did-it-move attribution for every ±3% session, and the **company-response read** (what management is *doing* about each headwind: IMPROVING / WORSENING / COSMETIC). Feeds the levels registry (`not_before`/`expires` around binaries), tax-aware Path B, and the per-name **catalyst map** section every report requires. Its **Tier S** is the pre-positioning playbook: forecast probable-but-unannounced events (renewal calendars, concentration disclosures, duopoly gaps) and buy the *setup* that carries announcement optionality — with sell-the-news discipline decided in advance.
- `analysis/macro-regime.md` — top-down weather: Fed path, rates, VIX, breadth; regime tilt.
- `analysis/crisis-playbook.md` — crash/regime-shock manual: survive + hunt (phase map + case studies 2000/2008/COVID/2025/2026). Invoked by macro-regime.
- `analysis/sector-playbooks.md` + `sectors/` — per-industry "what sets the price + where the catalyst hides." One file per sector.
- `analysis/stocks/` — per-name stock playbooks: how a specific ticker trades (repeating setups, catalyst calendar, dated episodes). One file per ticker.

## decision/ — decide, size, protect
- `decision/roles.md` — charter for each desk role (who does what, independently).
- `decision/research-debate.md` — structured multi-round Bull-vs-Bear + Research-Manager stance (Step 5). *(From TradingAgents.)*
- `decision/risk-committee.md` — three-lens risk debate (aggressive/neutral/conservative) + Risk Judge (Step 7). *(From TradingAgents.)*
- `decision/review-rubric.md` — scoring, hard gates, sleeves, position sizing.
- `decision/stress-test.md` — adversarial questioning: if→then audit, two-sided catalysts, load-bearing assumptions, pre-mortem. The bear's ammunition.
- `decision/sufficiency-gate.md` — the reviewer's question before ANY actionable call ships (full run or ad-hoc): *"have you collected enough information and done enough quant analysis?"* — dated + priced-in facts, 72h tape, strongest opposing fact named, full engine suite w/ disagreements reported, adversarial verify on stake-heavy/reversal calls; reviewer ≠ author.
- `decision/strategies.md` — exit discipline, rank-and-rotate, validation patterns.
- `decision/sell-timing.md` — popular/momentum exits: ride the overshoot, leave before the give-back. Six distribution tells (extension, distribution days, OBV divergence, climax, chip saturation, give-back) → RIDE / TIGHTEN / TRIM / EXIT with a printed stop ladder (`../scripts/analysis/exit_radar.py`); sell into strength; the ratchet never surrenders >⅓ of peak gain. Runs on every holding up ≥30% at every desk run.
- `decision/weekly-retrospective.md` — weekly continuity and calibration: `../scripts/journal/weekly_review.py` re-reads reports, marks the open book, scores mature calls, and updates rules only after repeated evidence.
- `decision/insight-registry.md` — machine-readable, expiring method hypotheses in the private journal; out-of-sample scoring determines which signals earn attention.
- `decision/reflection-memory.md` — the learning loop: log, score raw + alpha-vs-SPY, one lesson, recall into future runs. *(From TradingAgents.)*
- `decision/tax-aware.md` — holding-period, wash-sale, tax-loss-harvest rules.
- `decision/trading-modes.md` — shared execution-authority switch: `semi` is the public default (numbered tickets the user approves); `manual` is the per-order kill switch; `full` requires explicit user opt-in.

## playbook/ — the user's context (bring-your-own; git-ignored overlay in `skills/private/`)
- `playbook/mentor-method.md` — undervalued-quality + 2x path, management read, 25% concentration cap.
- `playbook/mentor-casebook.md` — a mentor's philosophy + dated track record as a calibration pattern-library.
- `playbook/house-views.md` — your macro/technical heuristics.
- `playbook/watchlist-theses.md` — names you track; re-validate before acting.
- `playbook/options.md` — preferred option structures + account option-level constraint.
- `playbook/private-deals.md` — venture DD framework (separate, non-tradable track).

## execution/
- `execution/data-and-execution.md` — broker tool map, account/watchlist config, preview discipline, and mode-gated authorization rules.

## scripts/ (`../scripts/`)
The canonical grouped inventory is in [`../scripts/README.md`](../scripts/README.md). Key memory
tools are `../scripts/journal/desk_memory.py`, `../scripts/journal/mentor_history.py`, and
`../scripts/journal/weekly_review.py`; analysis, report, library, and operations tools live in
their matching subdirectories.

---

## Flow
1. **Weather & wave** (macro-regime + thematic-waves) — what belongs on the page today, where money is rotating.
2. **Edge** (variant-perception) — force a differentiated, evidenced thesis.
3. **Analysis** (sector + quant + smart-money) — build and time it with primary-source depth.
4. **Discipline** (rubric + debate + risk + tax) — decide, size, protect.
5. **User context** (mentor + house-views) — tilt and personalize throughout.

## Extending
- **New sector** → add `analysis/sectors/<name>.md` from `_TEMPLATE.md`, register in `analysis/sector-playbooks.md`.
- **New stock playbook** → add `analysis/stocks/<TICKER>.md` from `stocks/_TEMPLATE.md`, register in `stocks/README.md`.
- **New wave** → extend `edge/thematic-waves.md`.
- **New signal** → new file in the right group; wire into `decision/roles.md` + the rubric; update this map.
- Every sub-skill: self-contained, skimmable — purpose → framework → guardrails.
