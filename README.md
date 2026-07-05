<div align="center">

# 📈 AI Trader

**An open-source AI trading desk you run with your coding agent —
plus an open library of trading playbooks the community builds together.**

*It works like a small trading company: analysts research, a committee debates,
a risk manager sizes, and only the best ideas reach you.*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)
![Agent](https://img.shields.io/badge/agent-Claude%20Code%20%7C%20Codex-8A2BE2)
![Not financial advice](https://img.shields.io/badge/⚠️-not%20financial%20advice-red)

🎯 [What It Does](#-what-it-does) ·
🏛️ [The Desk](#️-the-desk) ·
🌍 [Knowledge Commons](#-the-knowledge-commons) ·
📄 [Sample](#-sample-report) ·
⚡ [Quickstart](#-quickstart) ·
🧩 [Make It Yours](#-make-it-yours) ·
🔌 [Brokers](#-broker-support) ·
🔒 [Privacy Gate](#-privacy--the-pii-gate) ·
🤝 [Contributing](#-contributing) ·
🙏 [Credits](#-acknowledgements--citation)

</div>

> ⚠️ **Not financial advice.** This is research tooling. By default it **never trades on its
> own** — you confirm every order. Markets carry risk; you alone are responsible for your trades.

> 🔗 **A broker connection is required.** Connect at least one **Robinhood agentic-trading
> account** (or another connector with the same data + trading functions — IBKR/Futu adapters
> planned). The desk pulls quotes, historicals, fundamentals, positions, and buying power through
> it. Without one, it falls back to web + manual data, which is much more limited. Set it up from
> a **CLI agent, not a desktop app** (see [Brokers](#-broker-support)).

---

## 🎯 What It Does

Three main ways to use it:

**1. On-demand analysis — ask anytime**
- *"Do a desk run on NVDA."* · *"How does the semiconductor sector look?"* · *"Review my
  watchlist — anything worth buying?"*
- Works at any level: a whole **industry/sector**, a single **stock**, or your full watchlist.
- You get a research report with the analysis, a trade plan (entry / stop / target / size), and a
  clear **buy / wait / pass** call.

**2. Scheduled reports — the desk runs itself on a timer**
- Set a recurring run (your agent's scheduler, or cron) over your **watchlist and brokerage
  portfolio**.
- Each run delivers a styled HTML report with **short-term (tactical)** and **long-term (core)**
  recommended actions.
- It's honest: most days the right answer is *"nothing clears the bar today."*

**3. Trade execution — recommend, approve, place**
- The default flow: the **agent recommends → you approve → it places the order** through a broker
  like a **Robinhood Agentic Account**.
- Out of the box, nothing is ever bought or sold without your confirmation.
- Power users can tweak the skill files to automate more of the loop — up to a fully automatic
  trading tool. That's your call and your risk; the shipped default always asks first.

---

## 🧭 Overview

Most "AI stock picker" projects chase more signals. A real trading desk makes money by being
**selective** and **managing risk**. AI Trader encodes that discipline as a team of independent
roles that argue, stress-test, and vote — and that usually answers *"nothing clears the bar
today."*

How it's built:

- **Agent-driven.** The intelligence lives in plain skill files ([`SKILL.md`](SKILL.md) +
  [`skills/`](skills/)) that your AI coding agent reads. Pure-Python engines handle the math.
- **No LLM API key needed** for the default mode — your coding agent *is* the brain. You do need
  a broker connection for market data.
- **Structured disagreement.** A multi-round bull-vs-bear debate and a three-lens risk committee
  mean no idea wins by assertion. *(Architecture inspired by
  [TradingAgents](#-acknowledgements--citation).)*
- **It learns.** Every call is logged, scored against SPY (alpha, not just raw return), and turned
  into a lesson the desk recalls on the next similar setup.
- **It compounds community knowledge.** Sector and stock playbooks are written by people who know
  the industry, reviewed in the open, and read by every desk that forks this repo
  ([Knowledge Commons](#-the-knowledge-commons)).
- **Privacy built in.** A PII gate blocks account numbers, keys, and personal data from ever
  reaching a public branch.

> 🌱 **This is the open-source starter.** It ships general trading knowledge only — no personal
> positions, no proprietary edge. **Fork it and make it yours:** add your watchlist, house views,
> and broker. Your customizations live in git-ignored overlays, so a private desk sits on top of a
> public base.

---

## 🏛️ The Desk

AI Trader is organized like a real trading company, and it runs like a winning team:

- every seat has a written charter,
- nobody grades their own homework,
- and even the star idea has to survive the committee.

Specialists produce independent work, a research committee debates it, a risk committee sizes it,
and a CIO gate lets only high-edge ideas through.

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/desk-flow-dark.svg">
  <img src="docs/desk-flow.svg" width="820" alt="AI Trader pipeline: your coding agent orchestrates the desk — macro/regime, thematic wave, quant/chip engine, and the analyst team feed a research debate and risk committee; the CIO gate passes only high-edge ideas into a report, which you approve before the broker places any order; lessons are logged and recalled on the next run.">
</picture>
</div>

### 👥 Analyst Team
Four independent lenses, each doing primary-source work (details in
[`skills/decision/roles.md`](skills/decision/roles.md)):
- **Fundamental** — business quality, valuation, strategy and product pipeline, management,
  scenario targets.
- **Quant** — trend/momentum/volume, the **support & resistance map**, ATR-scaled risk:reward, and
  the **chip / cost-basis distribution** + Wyckoff phase.
- **Sentiment / News** — dated catalysts, positioning, insider flows, and *what isn't in the
  narrative yet*.
- **Macro / Regime** — Fed path, yields, VIX, breadth; a crisis playbook when the tape breaks.

### ⚔️ Research Debate — *bull vs bear → Research Manager*
A **multi-round** debate ([`skills/decision/research-debate.md`](skills/decision/research-debate.md)):
the bull argues the thesis, the bear attacks it, each must answer the other's strongest point —
then a Research Manager **commits to a stance** (Strong Buy … Sell) and never hides behind "Hold."

### 🛡️ Risk Committee — *three lenses → Risk Judge*
Aggressive, Neutral, and Conservative lenses debate the *trade plan*
([`skills/decision/risk-committee.md`](skills/decision/risk-committee.md)); the Risk Judge then
**approves, resizes, or vetoes**, enforcing hard limits (RR ≥ 2, ≤ 2% risk per idea, ≤ 25% per
name, regime tilt).

### 🧠 Reflection & Memory — *the desk learns*
Every call is logged. When the outcome is known, it's scored (raw return **and** alpha vs SPY) and
distilled into one reusable lesson, recalled on the next similar setup
([`skills/decision/reflection-memory.md`](skills/decision/reflection-memory.md)).

---

## 🌍 The Knowledge Commons

No single trader knows how every industry — or every stock — prices. A semis veteran reads node
yields; a biotech specialist reads trial design and cash runway; a bank analyst reads credit
cycles. This repo collects that craft in one open place, and every desk built on it reads the
result on its next run.

Contributed knowledge lives at three levels:

- **Sector / industry playbooks** — [`skills/analysis/sectors/`](skills/analysis/sectors/): how an
  industry prices (drivers, catalysts, valuation lens, red flags).
- **Stock playbooks** — [`skills/analysis/stocks/`](skills/analysis/stocks/): how a specific name
  trades — repeating setups, catalyst calendar, dated episodes. Knowledge, never a live call.
- **Trading & analysis skills** — strategy patterns (`skills/decision/`), edge signals
  (`skills/edge/`), engine improvements.

The loop is simple:

1. Write it from the matching `_TEMPLATE.md`.
2. It's reviewed in the open against a [quality bar](CONTRIBUTING.md#the-playbook-quality-bar):
   **specific · falsifiable · primary-sourced · dated · illustrated · general**.
3. It merges, and every fork's analyst team picks it up on its next run.

Coverage maps and the wanted list (banks, REITs, oil & gas, industrials, healthcare, mining, …)
are in [`skills/analysis/sectors/README.md`](skills/analysis/sectors/README.md) and
[`skills/analysis/stocks/README.md`](skills/analysis/stocks/README.md).

Nothing here is a black box: every rule the desk follows — the debate protocol, the risk gates,
the sizing math — is plain markdown you can read, audit, and edit. Contributions carry knowledge,
never positions (the PII gate enforces it), and the desk scores its own calls against SPY, so the
process keeps a track record.

---

## 📄 Sample report

See what a run produces: **[`reports/sample-report.html`](reports/sample-report.html)** — a real
desk run (sanitized), one self-contained HTML file with charts inlined. Open it in a browser, or
view it without cloning via a raw-HTML previewer (prepend `https://htmlpreview.github.io/?` to the
file's GitHub URL).

The sample (a July 2026 run over **INTC · MRVL · NKE · SOFI · KMX**) shows the format:

- **Summary → Action → Breakdown**, written for a non-finance reader.
- Colour-coded **callouts** — green ACTION (the trade), amber WATCH (wait for a level), RISK (what
  kills it), NOTE (cash/sizing).
- Per-name **charts** — price/volume with the support/resistance ladder, the chip-distribution
  histogram, and RSI/Stochastic/ADX gauges.
- A sized **trade plan** per idea (entry / stop / target / % risk), short- vs long-run calls, and
  cash management around event dates.
- The **discipline**: what to buy, what to *wait* for, and where it holds cash instead of forcing
  a trade.

> Illustrative only — a demo of the output format, not investment advice.

---

## ⚡ Quickstart

> 🤖 **Easiest path: hand this README to your AI agent.** Share this file (and
> [`SKILL.md`](SKILL.md)) with your CLI agent — Claude Code or Codex — and say *"read this and set
> it up, then run a desk run for me."* The toolkit is designed to be operated by an agent reading
> these docs: it can install the PII gate, wire your config, connect the broker, and run the desk
> end to end. The steps below are the same thing done by hand.

```bash
git clone <your-fork-url> ai-trader && cd ai-trader
cp config.example.toml config.local.toml   # add your broker/account (git-ignored)
cp .env.example .env                       # only if you use an API-key feature
bash scripts/install_hooks.sh              # install the PII gate (recommended)
```

Then point your agent at the skill and ask for a run:

- **Claude Code** — the repo's [`SKILL.md`](SKILL.md) *is* the skill.
- **Codex / any AGENTS.md agent** — [`AGENTS.md`](AGENTS.md) routes it in.
- See [`PORTABILITY.md`](PORTABILITY.md) to wire every runtime to one source folder.

> 💡 **Use a CLI agent (Claude Code or Codex), not a desktop app.** Desktop apps run in a
> restricted sandbox that often blocks broker connectors, scripts, and order placement. The CLI
> can run the engines, hold the broker connection, and place confirmed orders end to end.

The desk pulls data, runs the pipeline, and returns a ranked, risk-checked report — or an honest
"nothing clears the bar." No broker connector? It falls back to web data + a historicals JSON you
supply (see *Portability & capability detection* in `SKILL.md`).

### Use the engines standalone (no agent)

```bash
# Indicators + S/R map + chip distribution:
python3 scripts/indicators.py path/to/historicals.json --price 128.40 --float 4100000000

# The learning journal:
python3 scripts/track_record.py recall --symbol NVDA
python3 scripts/track_record.py report            # win rate + avg alpha + recent lessons
```

Pure Python standard library — no dependencies, runs anywhere `python3` does.

---

## 🧩 Make It Yours

The repo ships **generic starter templates** — replace them with your own edge:

| File | Put here |
|---|---|
| `skills/playbook/house-views.md` | Your macro/technical heuristics |
| `skills/playbook/watchlist-theses.md` | Names you track + thesis + invalidation |
| `skills/playbook/mentor-method.md` · `skills/playbook/mentor-casebook.md` | The method/investor you study |
| `skills/analysis/sectors/` | Add a sector playbook via `sectors/_TEMPLATE.md` |
| `skills/analysis/stocks/` | Add a stock playbook via `stocks/_TEMPLATE.md` |

**Keep private content private.** Anything under `skills/private/` is **git-ignored** — put a
confidential watchlist, a paid newsletter's live book, or a private deal there and it never lands
in your fork's public history.

---

## 🔌 Broker Support

**A connected broker is required.** The desk pulls quotes, historicals, fundamentals, positions,
and buying power through it — that data drives most of the research.

| Broker | Status | Notes |
|---|---|---|
| **Robinhood** | ✅ working (via connector) | Quotes, historicals, fundamentals, positions, confirm-before-order execution. |
| **Interactive Brokers** | 🔌 planned | Adapter interface + config slot ship now; implementation welcome. |
| **Futu / moomoo** | 🔌 planned | Same. |

### Robinhood: connect your AI agent (agentic trading)

Robinhood's **agentic trading** connector lets an AI agent read your data and place orders (with
confirmation). Follow Robinhood's official setup:

➡️ **[Robinhood — Agentic Trading Overview → *Connect your AI agent*](https://robinhood.com/us/en/support/articles/agentic-trading-overview/#ConnectyourAIagent)**

> 💡 **Do this from a CLI agent, not a desktop app.** The desktop sandbox commonly blocks the
> connector and order placement. Enable the connector, then put the authorized account into
> `config.local.toml` (git-ignored). The desk still **confirms every order with you before
> placing it** unless you change that default.

The design goal is **one broker-adapter interface** — add a broker by implementing a single class.
See [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 🔒 Privacy & the PII Gate

Publishing trading tooling means **never leaking your account or positions.** This repo enforces
it with three layers:

- **Secrets live only in git-ignored files** — `config.local.toml`, `.env`, `skills/private/`.
- **A scanner** — [`scripts/scan_pii.py`](scripts/scan_pii.py) — flags account numbers, keys,
  connector UUIDs, and personal identifiers in tracked files.
- **A three-layer gate**: a pre-commit hook, a pre-push hook, and CI
  ([`.github/workflows/pii-scan.yml`](.github/workflows/pii-scan.yml)) — the server-side backstop
  that can't be skipped.

```bash
bash scripts/install_hooks.sh          # turn on the local gate
python3 scripts/scan_pii.py            # scan on demand before publishing
```

Add your exact private strings to `scripts/pii_denylist.local.txt` (git-ignored) for hard
blocking.

---

## 🤝 Contributing

Issues and PRs welcome. The highest-leverage contribution is a playbook — sector/industry or
single-stock (see [The Knowledge Commons](#-the-knowledge-commons)); broker adapters, engine
improvements, and docs are close behind. Open a **playbook proposal** issue to claim one, and run
`python3 scripts/scan_pii.py` before pushing. Full guide + quality bar:
[`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 🙏 Acknowledgements & Citation

The structured **bull/bear research debate**, **multi-perspective risk committee**, and
**reflection/memory** design are inspired by **TradingAgents** (Tauric Research). If you build on
this work, please also credit theirs:

```bibtex
@misc{xiao2025tradingagents,
  title        = {TradingAgents: Multi-Agents LLM Financial Trading Framework},
  author       = {Xiao, Yijia and Sun, Edward and Luo, Di and Wang, Wei},
  year         = {2025},
  eprint       = {2412.20138},
  archivePrefix= {arXiv},
  primaryClass = {q-fin.TR}
}
```

---

## ⚖️ Disclaimer & License

AI Trader is for **research and education only** and is **not financial or tax advice**. By
default it does not auto-trade — you approve and place every order. If you modify it to automate
execution, you do so at your own risk and own every outcome. Past performance and backtests do
not guarantee future results.

Licensed under the terms in [`LICENSE`](LICENSE).
