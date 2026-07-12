# Valuation & Quality Gate — definers need a quality floor and a price ceiling

Adapted from ai-berkshire (`quality-screen`, `investment-research` Module 7). The desk's
secular-wave method finds *where* value concentrates; this gate stops it from (a) labeling
a low-quality momentum name a "definer" and (b) holding a great business at a price that
already assumes the whole future. Both checks are **scripts, never LLM mental math** —
the desk gathers inputs from primary sources (10-K, press releases) with citations; the
scripts apply the rules.

## 1. Quality gate — required before any "definer/hold" classification

`python3 scripts/analysis/quality_gate.py metrics/<ticker>.json [--exempt "filter=type: why"]`

Seven disqualifiers (eliminate confirmed-bad, don't certify good): 10-yr avg ROE <8% ·
5-yr cumulative FCF negative · interest coverage <2x · gross margin <15% · 5-yr OCF/NI
<0.7 · net margin <5% · 5-yr dilution >20%. Three exemption types, each requiring a
written justification: `growth-stage`, `reinvestment`, `high-turnover` (Costco-style).

**Rules:**
- A ticker **cannot be classified "definer/hold"** in a report without `PASS` or
  `PASS (with exemptions)`. `INCOMPLETE` (unknown metrics) is not a pass — say so.
- **Spikers may bypass** with an explicit `SPIKER — quality gate waived` tag in the
  report. The waiver must be visible; ride-with-stops rules apply, never "hold".
- Gate inputs and their sources are quoted in the report appendix (≥1 primary source;
  flag any figure the desk could not verify).

## 2. Reverse DCF — every "hold" carries the growth rate its price implies

`python3 scripts/analysis/reverse_dcf.py --mcap <$> --fcf <TTM$>` → "price implies X%/yr FCF
growth for 10 years." One number that exposes an overextended definer instantly.
Reads: ≥25%/yr = very demanding (justify or trim) · 15–25% = demanding (compare to
actual growth) · 5–15% = reasonable · <5% = market prices stagnation (potential value).

## 3. Three-scenario ceiling — holds get exit bands, not just entry bands

`python3 scripts/analysis/reverse_dcf.py --fcf <$> --shares <n> --price <px> --scenarios
0.20:25 0.12:18 0.05:12` (optimistic/base/pessimistic growth:exit-multiple) →
per-share fair values. **The optimistic-scenario value is the hold's price ceiling** —
register it in `journal/action-levels.jsonl` as a `direction: above` TRIM/REVIEW alert,
so every definer has an exit band in the same registry as its entry band.

## Where it hooks into the process

- **Report vocabulary:** "definer" / "hold" / "spiker" tags in any report must carry
  `[QG: PASS]`, `[QG: PASS w/ exemption]`, or `[SPIKER — QG waived]`, plus an
  `implied growth: X%/yr` line on every hold.
- **Insight registry:** quality/valuation-driven calls tag `quality-value` as a method,
  so the scorer can tell whether the fundamental layer adds hit-rate over the technical.
- **Order of operations:** wave/layer thesis → ownership gate → phase/chips →
  **quality gate → reverse DCF** → sizing (rubric) → levels registry. The gate runs
  before sizing, never after the position exists.
