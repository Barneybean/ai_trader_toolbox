# Business Inflection — the "next big things" read: what's changing in the business, and how the Street re-prices it

Technical and valuation work can score the *trade* while missing changes in the *company*—
strategic pivots that alter what investors believe the profit model is. This protocol makes that
forward business read explicit. Large re-pricings often occur when the market reclassifies what
kind of business it is evaluating, not merely when a support level holds.

Run it: **mandatory section in every single-name deep dive**; refresh for held names each
earnings cycle; trigger ad-hoc on an 8-K reorg, a leadership change, a guidance-framework
change, or when call language shifts (below).

## Step 1 — Inventory the inflections (what counts)

Scan for changes in these nine categories — each one is a potential re-pricing event:

1. **New profit engine** — a product/segment going from "project" to "P&L line" (and the
   reverse: a bet being wound down).
2. **Monetization-model change** — how the same asset gets paid for (ads → AI-priced ads,
   license → subscription, free → paid tier, take-rate changes).
3. **Capital-intensity pivot** — capex step-changes (AI infrastructure buildouts), buy-vs-build
   shifts, asset-light → asset-heavy or back. Capex is strategy stated in dollars.
4. **Segment-disclosure change** — when a company breaks out (or buries) a segment in its
   filings, management is telling you what it wants to be judged on. Highest-signal, least
   watched.
5. **Org / leadership restructure** — new CEO/CFO/division heads, reorgs around a priority,
   mass reallocation of headcount ("efficiency" years, AI-team consolidations).
6. **Capital-return regime** — first dividend, buyback inflection, leverage policy change.
   These re-classify the stock for whole investor bases (growth funds ↔ income funds).
7. **Guidance-framework change** — new KPIs introduced or old ones retired on the call
   (companies stop guiding what's about to look bad; start guiding what's about to look good).
8. **Regulatory / geopolitical reshaping** — rulings, export controls, antitrust remedies that
   change the addressable market or cost structure, not just headlines.
9. **M&A and partnerships** — what the company just bought/allied says where it thinks its
   next decade is.

**Detection sources, tiered (desk evidence discipline applies):** consecutive earnings-call
transcripts read as a *delta* — what language appeared, what vanished, where the CEO spends
minutes vs last quarter (tier 1); filings — segment tables, capex lines, risk-factor edits,
8-Ks (tier 1); hiring pages, capex announcements, customer/partner roadmaps (tier 2); press
and social chatter (tier 3 — never size off it).

## Step 2 — Map each inflection to the stock (the two channels)

Every inflection reaches the price through one or both channels — name which, explicitly:

- **Estimates channel (the numbers):** does it change revenue (TAM, growth rate, pricing),
  margin structure (mix, opex discipline, D&A from capex), capital intensity (FCF conversion),
  or the EPS path? Quantify roughly: what does the consensus model assume today, what would it
  assume if this inflection works? `reverse_dcf.py` shows what growth is currently priced in.
- **Multiple channel (the narrative):** does it change *what kind of company* the market files
  this under? "Ad company" → "AI company", "hardware" → "recurring software", "growth" →
  "capital returner" — reclassification moves the multiple even before estimates move, because
  different investor bases apply different frameworks. Evidence: multiple vs its own history,
  vs the peer set the Street quotes it against, and *which* peer set analysts now use.

Then the money question per inflection: **is it priced?** Checks: sell-side estimate-revision
trend (already migrating?), whether the narrative appears in upgrade/downgrade arguments, the
multiple's re-rate to date, positioning (crowded = priced). Unpriced + tier-1/2 evidence =
edge; fully narrated = consensus beta (variant-perception rule applies unchanged).

## Step 3 — Score and verdict

For each inflection, one row (this table is the report deliverable):

| Inflection | Evidence (tier · date) | Channel | Street's current read | Desk view | Priced? | Clock |
|---|---|---|---|---|---|---|

- **Materiality gate:** estimate the share of company value the inflection can plausibly touch
  (rough %). Below ~10% of value → watch-list line, not thesis material.
- **Proof-over-promise** (`industry-map.md` rule): a shipping product with disclosed revenue
  outweighs a keynote demo; a capex line outweighs a vision statement.
- **Clock:** the dated event that forces the Street to update (segment first disclosed,
  guidance raised, product GA, ruling date) — feeds the catalyst map and the two-horizon clock.
- **Net verdict:** the single sentence a report reader needs — "the market still prices X as
  ___; the business is becoming ___; the gap closes when ___."

## How it wires into the desk

- **Step 4 (Fundamental):** this read is part of the Fundamental specialist's deep-dive
  workup — the "strategy & roadmap" line item, made systematic. The verdict feeds the
  variant-perception statement directly (consensus view of the business vs what it's becoming).
- **Catalyst scan:** every inflection's Clock lands in the forward calendar with
  direction-if-hit.
- **Continuity:** inflection theses are logged (`watchlist-theses.md` for tracked names,
  insight registry for scored calls) and re-graded every earnings call in the weekly
  retrospective — did management's language/numbers advance, stall, or reverse?
- **Options overlay:** when the user's private policy permits options, a dated re-pricing clock
  with defined risk may support an appropriately long-dated structure (`playbook/options.md`).

## Guardrails

- **Narrative-chasing risk:** by the time a "next big thing" is the headline, it's usually the
  multiple. The edge is in inflections visible in filings/capex/org changes but absent from
  upgrade notes — the same low-attention logic used throughout variant-perception work.
- **Management-hype discount:** every CEO pitches a next big thing; the desk grades what they
  *spend and reorganize around*, not what they say. Cross-check with the company-response read
  (IMPROVING / WORSENING / COSMETIC) in `catalyst-scan.md`.
- **Bets can be liabilities:** a next big thing that consumes FCF for years with no proof point
  is a bear-case input (the capex question cuts both ways). Score direction honestly.
- **≥ tier-2 evidence to size;** tier-3 narrative alone never moves a position.
