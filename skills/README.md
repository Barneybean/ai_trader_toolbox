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

## analysis/ — how to analyze a name
- `analysis/quant-levels.md` — the level engine: support/resistance map, ADX, momentum, ATR stops, RR/EV (drives `../scripts/indicators.py`).
- `analysis/chip-distribution.md` — institutional footprint: Wyckoff phase, chip/cost-basis distribution (筹码), accumulation vs. distribution, anticipating chip washes (洗盘).
- `analysis/macro-regime.md` — top-down weather: Fed path, rates, VIX, breadth; regime tilt.
- `analysis/crisis-playbook.md` — crash/regime-shock manual: survive + hunt (phase map + case studies 2000/2008/COVID/2025/2026). Invoked by macro-regime.
- `analysis/sector-playbooks.md` + `sectors/` — per-industry "what sets the price + where the catalyst hides." One file per sector.

## decision/ — decide, size, protect
- `decision/roles.md` — charter for each desk role (who does what, independently).
- `decision/research-debate.md` — structured multi-round Bull-vs-Bear + Research-Manager stance (Step 5). *(From TradingAgents.)*
- `decision/risk-committee.md` — three-lens risk debate (aggressive/neutral/conservative) + Risk Judge (Step 7). *(From TradingAgents.)*
- `decision/review-rubric.md` — scoring, hard gates, sleeves, position sizing.
- `decision/stress-test.md` — adversarial questioning: if→then audit, two-sided catalysts, load-bearing assumptions, pre-mortem. The bear's ammunition.
- `decision/strategies.md` — exit discipline, rank-and-rotate, validation patterns.
- `decision/reflection-memory.md` — the learning loop: log, score raw + alpha-vs-SPY, one lesson, recall into future runs. *(From TradingAgents.)*
- `decision/tax-aware.md` — holding-period, wash-sale, tax-loss-harvest rules.

## playbook/ — the user's context (bring-your-own; git-ignored overlay in `skills/private/`)
- `playbook/mentor-method.md` — undervalued-quality + 2x path, management read, 25% concentration cap.
- `playbook/mentor-casebook.md` — a mentor's philosophy + dated track record as a calibration pattern-library.
- `playbook/house-views.md` — your macro/technical heuristics.
- `playbook/watchlist-theses.md` — names you track; re-validate before acting.
- `playbook/options.md` — preferred option structures + account option-level constraint.
- `playbook/private-deals.md` — venture DD framework (separate, non-tradable track).

## execution/
- `execution/data-and-execution.md` — broker tool map, account/watchlist config, confirm-before-every-order guardrails.

## scripts/ (`../scripts/`)
`indicators.py` (quant engine) · `charts.py` (SVG charts) · `build_report.py` (HTML) · `new_report.py` (scaffold) · `track_record.py` (journal + reflection) · `install_hooks.sh` / `scan_pii.py` (PII gate) · `install_mirrors.sh` / `package_skill.py` (runtime wiring).

---

## Flow
1. **Weather & wave** (macro-regime + thematic-waves) — what belongs on the page today, where money is rotating.
2. **Edge** (variant-perception) — force a differentiated, evidenced thesis.
3. **Analysis** (sector + quant + smart-money) — build and time it with primary-source depth.
4. **Discipline** (rubric + debate + risk + tax) — decide, size, protect.
5. **User context** (mentor + house-views) — tilt and personalize throughout.

## Extending
- **New sector** → add `analysis/sectors/<name>.md` from `_TEMPLATE.md`, register in `analysis/sector-playbooks.md`.
- **New wave** → extend `edge/thematic-waves.md`.
- **New signal** → new file in the right group; wire into `decision/roles.md` + the rubric; update this map.
- Every sub-skill: self-contained, skimmable — purpose → framework → guardrails.
