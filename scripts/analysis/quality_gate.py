#!/usr/bin/env python3
"""Quality gate — 7 mechanical disqualifiers before any "definer/hold" classification.

Adapted from ai-berkshire's quality-screen skill. The gate eliminates "confirmed
bad," it does not certify good. The desk (LLM) gathers the inputs from PRIMARY
sources (10-K, press releases) with citations; this script only applies the rules
— no LLM mental math, no data fetching.

Input: a JSON file (or inline --metrics JSON) with:
  {"ticker": "SYM",
   "roe_10y_avg": 0.14,            # 10-yr average ROE (or as many years as exist)
   "fcf_5y_cum": 1.2e9,            # 5-yr cumulative free cash flow, $
   "interest_coverage": 8.5,       # EBIT / interest expense (null if no debt)
   "gross_margin": 0.22,           # latest FY
   "ocf_to_ni_5y": 1.1,            # 5-yr operating cash flow / net income
   "net_margin": 0.06,             # latest FY
   "dilution_5y": 0.04}            # 5-yr increase in shares outstanding (0.04 = +4%)

Filters (FAIL if):        roe_10y_avg < 0.08 | fcf_5y_cum < 0 | interest_coverage < 2
                          gross_margin < 0.15 | ocf_to_ni_5y < 0.7 | net_margin < 0.05
                          dilution_5y > 0.20
Exemptions (--exempt filter=reason, repeatable):
  growth-stage       — pre-profit scale-up with unit economics improving (justify)
  reinvestment       — margins depressed by deliberate strategic reinvestment (justify)
  high-turnover      — low-margin/high-velocity model (Costco-style; gross/net margin only)
Missing metrics are reported as UNKNOWN — a gate with unknowns is NOT a pass.

Usage:
  python3 scripts/analysis/quality_gate.py metrics/sym.json
  python3 scripts/analysis/quality_gate.py --metrics '{"ticker":"SYM",...}' --exempt "net_margin=growth-stage: EBITDA turned positive FY25, scaling"
"""
import argparse
import json
import sys

FILTERS = [
    ("roe_10y_avg",       lambda v: v < 0.08,  "10-yr avg ROE < 8%"),
    ("fcf_5y_cum",        lambda v: v < 0,     "5-yr cumulative FCF negative"),
    ("interest_coverage", lambda v: v < 2,     "interest coverage < 2x"),
    ("gross_margin",      lambda v: v < 0.15,  "gross margin < 15%"),
    ("ocf_to_ni_5y",      lambda v: v < 0.7,   "5-yr OCF/NI < 0.7 (earnings not cash-backed)"),
    ("net_margin",        lambda v: v < 0.05,  "net margin < 5%"),
    ("dilution_5y",       lambda v: v > 0.20,  "5-yr share dilution > 20%"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="JSON file with metrics")
    ap.add_argument("--metrics", help="inline JSON metrics")
    ap.add_argument("--exempt", action="append", default=[],
                    metavar="FILTER=TYPE: justification",
                    help="e.g. --exempt 'net_margin=growth-stage: EBITDA positive, scaling'")
    args = ap.parse_args()

    if args.metrics:
        m = json.loads(args.metrics)
    elif args.file:
        with open(args.file) as f:
            m = json.load(f)
    else:
        ap.error("provide a metrics JSON file or --metrics")

    exemptions = {}
    for e in args.exempt:
        k, _, why = e.partition("=")
        exemptions[k.strip()] = why.strip()

    fails, exempted, unknown, passed = [], [], [], []
    for key, bad, desc in FILTERS:
        v = m.get(key, None)
        if v is None:
            # per the input contract, an EXPLICIT null interest_coverage means
            # "no debt" (as does a no_debt flag); only an absent key is unknown
            if key == "interest_coverage" and (m.get("no_debt") or key in m):
                passed.append((key, "no debt"))
                continue
            unknown.append((key, desc))
        elif bad(float(v)):
            if key in exemptions:
                exempted.append((key, desc, exemptions[key]))
            else:
                fails.append((key, desc, v))
        else:
            passed.append((key, v))

    t = m.get("ticker", "?")
    if fails:
        verdict = "FAIL"
    elif unknown:
        verdict = "INCOMPLETE"
    elif exempted:
        verdict = "PASS (with exemptions)"
    else:
        verdict = "PASS"

    print(f"QUALITY GATE — {t}: {verdict}")
    for k, desc, v in fails:
        print(f"  ✗ FAIL    {desc}  (={v})")
    for k, desc, why in exempted:
        print(f"  ~ EXEMPT  {desc}  — {why}")
    for k, desc in unknown:
        print(f"  ? UNKNOWN {desc} — gate incomplete, not a pass")
    for k, v in passed:
        print(f"  ✓ pass    {k} = {v}")
    print("\nRule: no 'definer/hold' classification without PASS or PASS-with-exemptions."
          "\n      Spikers may bypass with an explicit 'SPIKER — quality gate waived' tag.")
    return 0 if verdict.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
