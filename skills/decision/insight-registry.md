# Insight Registry — every call is structured, expiring, and scoreable

Adapted from LEAN's Algorithm Framework (`Insight.cs`): a prediction that isn't structured
can't be wrong, and can't be scored. The desk emits **every directional call as a JSON record**
in `journal/insights.jsonl` (git-ignored, personal data) and scores expired calls weekly.
This is the desk's feedback loop — it answers "which of my METHODS actually hits," not just
"was I right on average."

## The record

```json
{"id": "xyz-long-20260705", "ts": "2026-07-05", "ticker": "XYZ",
 "direction": "up",            // up | down | flat
 "magnitude": 0.30,            // expected move in direction, decimal
 "confidence": 0.60,           // 0-1; drives sizing (see rubric)
 "price_at_call": 100.00,
 "expires": "2027-07-05",      // every insight EXPIRES — no evergreen calls
 "methods": ["layer-rotation", "chip-distribution"],
 "thesis": "xyz-theme-definer",      // GroupId — links the two horizons of one thesis
 "source": "report_2026-07-05_...", "note": "…",
 "cancelled": false}
```

## Rules

1. **Every report recommendation emits insight records** — the two-horizons rule maps to
   **two insights per thesis** (short + long `expires`) sharing one `thesis` GroupId.
   A "no action / hold" call is a `flat` insight — it's still a scoreable prediction.
2. **Method tags are mandatory.** Registry vocabulary: `phase-map`, `chip-distribution`,
   `obv-footprint`, `layer-rotation`, `variant-perception`, `forecast-mc`, `mentor`,
   `quality-value`, `anticipated-catalyst` (pre-positioning for a probable-but-unannounced
   event per `skills/analysis/catalyst-scan.md` Tier S — the tag exists so scoring can tell
   whether the desk's event anticipation actually adds hit-rate). Add tags sparingly; they
   are only useful if reused. Scoring aggregates per tag — after ~30 scored insights,
   reweight desk attention toward what hits.
3. **Cancel on thesis break — and no re-entry on a stale insight.** When a stop fires or
   the thesis breaks, set `"cancelled": true` (LEAN's rule: liquidation must cancel the
   insight "to avoid re-entering the position"). Re-entry requires a **new** insight with
   a new date and rationale.
4. **Hypothesis first, then tools** (LEAN's anti-overfitting guide, translated): write the
   insight's direction/magnitude/falsification **before** running `forecast.py` or pulling
   chip data. Re-running the quant tools with tweaked windows until they agree with your
   prior is the discretionary version of 70 backtests — if tools were re-run 3+ times on
   one name, add `"reruns": N` and discount confidence.
5. **Score weekly, out-of-sample only:** `python3 scripts/journal/score_insights.py` (add `--mark`
   for open-position mark-to-market). Only price data after the call timestamp counts;
   "it would have worked if entered earlier" is not a hit.
6. Confidence → size lives in the rubric, not here: the insight states the view; the
   sizing table converts confidence to weight. Never size in the same breath as the thesis.

## Cadence

- **Every desk run:** append new insights; cancel broken ones.
- **Weekly (or first run of the week):** run the scorer; print the per-method table in the
  report ("desk hit-rates to date"). Honest reporting includes the misses.
