# Catalyst Scan — dated events + what the company is doing about them

Why this exists (two dated lessons, 2026-07): **ARE** dropped 5.2% in a session and the
cause (a Morgan Stanley downgrade to Underweight modeling SSNOI −8% and FFO −22%) was only
findable by an ad-hoc search *after* the fact; **RC**'s entire bull case (deleveraging: $1.4B
asset sales, $1.1B+$184M debt repaid, "BV pressure subsiding") *and* its bear case (a $650M
2026 maturity wall, asset sales clearing below book, SBA reg risk to the DTAs) were sitting
in an 8-K most holders had never opened. Price levels say **where** to act;
the catalyst map says **why the odds change and when**. Both are required.

## 1. When it runs (mandatory triggers)

- **Every name analyzed in a report** — new underwriting or re-underwriting. No verdict
  ships without the catalyst map section.
- **Any holding that moves ±3% in a session or gaps** — before the daily report is written,
  find the cause. "Dropped, cause unknown" is only allowed *after* a search, written as
  "searched — no attributable news" (which is itself a signal: flow-driven, not event-driven).
- **Any `check_alerts.py` trigger** — re-validation = `forecast.py` (the tape) **+ this scan**
  (the calendar). A level tagged the day before a binary is a different trade.
- **Any Path B harvest decision** (`skills/decision/tax-aware.md`) — the "no catalyst inside
  31 days" check is this scan, cited, not a guess.
- **Any mentor divergence** — before reconciling, pull the events both sides are trading on
  (the RC reconciliation turned entirely on the 8-K deleveraging plan vs the maturity wall).

## 2. The sweep — three questions per name

**A. Scheduled — what's on the calendar?** Next earnings date+time (`get_earnings_calendar`
or IR page), ex-div and declaration dates, guidance/investor days, product/launch events,
regulatory & court dates (FDA, DOJ, tariff decisions), **debt maturities and refi deadlines**
(the RC lesson — pull from the 10-Q/8-K, not headlines), index rebalances, lockup expiries.
Each entry gets a **date** and a **direction-if-hit**.

**B. Just happened — why did the tape move?** Fresh 8-Ks and press releases, analyst
up/downgrades *with the argument* (the thesis matters, the rating doesn't), dividend actions
(a cut is management's own forecast of earnings power), management changes (CFO/auditor exits
are red; operator-CEO hires are signal), M&A, insider Form-4 clusters (`skills/edge/smart-money.md`).
**Trailing-yield trap:** after any dividend cut, broker screens keep showing the *trailing*
yield for up to a year (RC showed 8.7% while the declared rate was $0.01/qtr = 2.4% forward).
Any income argument must use **declared rate × frequency ÷ price**, never the displayed yield —
and compare it to the cash sweep rate before calling it income.

**C. Company response — is management making the future better or worse?** For every
headwind found in A/B, ask: *what is the company doing about it*, and classify the action —

| Class | Looks like |
|---|---|
| **IMPROVING** | Deleveraging / asset sales at sensible prices; cost cuts with reinvestment; buybacks below intrinsic value; insider cluster buys; guidance raised on volume not price; capacity added against real (contracted) backlog |
| **WORSENING** | Dilutive raises at the lows; dividend cut to *preserve a broken model* (vs. redirect capital); asset sales below book; delayed filings; CFO/auditor exits; debt-funded buybacks at highs; guidance cuts blamed on "macro" while peers grow |
| **COSMETIC** | Reverse splits; renames; "exploring strategic alternatives" with no buyer named; token insider buys; adjusted-metric redefinitions |

Judge the **action against the balance sheet**, never the press-release adjective. The test:
*would a rational owner do this if the business were fine?* (RC's penny dividend + fire-sale
deleveraging answers itself; ARE's response to oversupply — occupancy defense vs. dilution —
is the next thing to check there.)

## 3. Sources, in order of trust

1. **Primary**: 8-K / 10-Q / press release / earnings transcript (SEC EDGAR, company IR).
2. **Broker connector**: `get_earnings_calendar`, `get_earnings_results`.
3. **Dated financial press** — cite with date; a headline without a primary source behind it
   is labeled *unverified*.

Every claim that reaches a report carries a **dated citation**. Confinement rule
(`skills/execution/data-and-execution.md`): searches use tickers and company names only —
never account data, position sizes, or anything from the private book.

## 4. Output — the catalyst map (required report section per name)

| Date | Event | Direction if… | Company action (class) | Source |
|---|---|---|---|---|
| 2026-08-0x | Q2 earnings | BV stabilizes → up big / drops >5% → exit | Deleveraging (IMPROVING, if sales ≥ ~book) | 8-K 6/xx |
| 2026 H2 | $650M maturities | refi fails → left tail | unresolved (WORSENING risk) | 10-Q |

Close with one line: **"Next binary: `<date>` `<event>` — positioning into it: `<hold through /
de-risk / gate adds / size-to-survive-the-tail>`."**

## 5. Tier S — anticipated catalysts (the pre-positioning playbook)

Sections A–C map what's *scheduled or already public*. Tier S hunts what's **probable but
unannounced** — and positions before the press release. The founding case (2026-07-06):
Broadcom +6.7% in a session on the Apple custom-ASIC extension through 2031. That event was
partially forecastable: it was a **renewal** of a known relationship (renewals have calendars),
Apple was a disclosed ~20%-of-revenue customer (concentration disclosures name the dance
partners), and the custom-ASIC market is a ~95% two-vendor market (AVGO + MRVL) — so *every*
hyperscaler silicon decision lands on one of two tickers. Structure like that makes
anticipation a tractable trade, not a lottery ticket.

**Where unannounced deals leave footprints (all public — never trade non-public information):**
- **Renewal calendars** — existing partnerships/contracts have terms; expiry windows are
  announcement windows. Log known deal end-dates in the map as Tier-S entries.
- **Concentration disclosures** — 10-K "customer >10% of revenue" lines and supplier lists
  name relationships before deal press releases do.
- **Duopoly/chokepoint structure** — when a layer has 2–3 credible vendors, any customer's
  decision must land on one of them. Map the dance floor: which customers have NOT announced
  a partner for the next generation (the gap is the trade).
- **Capacity and hiring footprints** — foundry/packaging allocations (CoWoS-class), tape-out
  chatter in Asia supply-chain press, design-center job postings naming the customer's stack.
- **Announcement venues** — earnings calls, WWDC/GTC/CES/investor days: deals cluster on
  dates. An expected-announcement venue inside the window raises P(event).
- **Sell-side channel checks** — weakest tier; use as corroboration, never as the thesis.

**How to trade it (mostly short-term, per the desk's ask):**
1. **Candidate matrix per theme:** customers (who needs silicon/capacity/distribution) ×
   vendors (who can supply) × status (announced / renewal-window / gap). Each gap gets a
   subjective **P(announcement ≤ 3–6mo)** and the likely winning ticker.
2. **Buy setups with announcement optionality — never rumors alone.** Pre-position only when
   the candidate ALSO passes the normal desk read (base/coil, chips supportive, quality gate
   or spiker tag). Then the trade is: technical setup pays if nothing happens; announcement
   is the free call option. Rumor-only entries are gambling and get vetoed.
3. **Size like an option:** starter/tactical size, defined stop from the technical setup —
   the event probability pads expected value but never justifies size (the event may simply
   not happen inside the window).
4. **Sell-the-news discipline, decided in advance:** write down *before* the event which one
   it is — (a) step-function that removes a bear case or re-rates earnings power (AVGO-Apple:
   definers keep it) → hold/re-rate; (b) sympathy/heat spike with no earnings change → trim
   into the spike (spiker rules). Announcement day is too late to decide.
5. **Register everything:** the insight carries method `anticipated-catalyst` + an `expires`
   at the end of the announcement window (unrealized anticipation must score as a miss, not
   roll forever); levels registry gets the trim/add bands. The scorer will eventually say
   whether the desk's anticipation hit-rate justifies the method.

**Report format:** Tier-S rows go in the same catalyst-map table, explicitly labeled
`SPECULATED (P≈x%)` — never mixed with confirmed calendar items. A reader must be able to
tell the desk's guesses from the company's filings at a glance.

## 6. Where it hooks into the process

- **SKILL.md Step 4 (Sentiment/News specialist)** — this file is that role's protocol.
- **Levels registry** (`journal/action-levels.jsonl`) — every binary date becomes registry
  hygiene: `not_before` / `expires` set around events (the META add-zone expiring before
  Jul-29 earnings is the pattern); a TRIGGERED level re-validates against the map before acting.
- **tax-aware Path B** — "no catalyst inside 31 days" cites this scan's calendar.
- **insight-registry** — set each insight's `expires` at/after the next binary and name the
  event in `note`, so scoring measures the call against the event that decides it.
- **stress-test** — section C's WORSENING list is the bear's ammunition; every catalyst gets
  its two-sided version there.
- **Daily desk run** — every ±3% mover gets a cause line with citation (or the explicit
  "searched, no attributable news").
