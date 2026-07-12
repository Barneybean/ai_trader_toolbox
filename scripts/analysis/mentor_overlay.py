#!/usr/bin/env python3
"""Mentor-overlay audit — compare the user's book against the mentor's, weight by weight.

The user's investing is heavily mentor-influenced, so the highest-signal risk check is
relative: where does the user hold MORE of something the mentor is exiting, or NOTHING
of a wing the mentor sizes seriously? (Founding case 2026-07: user held ~7% TSLA while
the mentor's sheet said SELL at <0.5% — a 14x relative overweight nobody had noticed.)

    python3 scripts/analysis/mentor_overlay.py positions.json [--mentor journal/mentor-book.json]

positions.json: [{"symbol": "NKE", "value": 108350.0}, ...]  (value = shares x price;
dump it from the connector at run time — this script never touches account data itself).

Flags:
  CONFLICT    mentor action is sell/trim and user weight > mentor weight
  OVERWEIGHT  user weight >= 2x mentor weight (mentor still buy/hold)
  MISSING     mentor weight >= 4% (buy) and user holds none — a conviction wing the
              user lacks; prompts a desk underwriting, NOT a copy-trade
  OFF-BOOK    user holds it, mentor doesn't — fine, but the desk owns 100% of the read

Output is analysis-only; per the confinement rules, never publish user values — the
report may show percentages and flags, not dollar amounts, outside private branches.
"""
import argparse
import json
import sys

FLAG_ORDER = {"CONFLICT": 0, "OVERWEIGHT": 1, "MISSING": 2, "OFF-BOOK": 3, "": 4}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("positions", help="JSON: [{symbol, value}] for the user's account")
    ap.add_argument("--mentor", default="journal/mentor-book.json")
    args = ap.parse_args()

    user = {p["symbol"].upper(): float(p["value"]) for p in json.load(open(args.positions))}
    book = json.load(open(args.mentor))["positions"]
    total = sum(user.values())
    if total <= 0:
        sys.exit("no user positions")

    rows = []
    for sym, m in book.items():
        uw = 100.0 * user.get(sym, 0.0) / total
        mw = m["weight"]
        flag = ""
        if m["action"] in ("sell", "trim") and uw > mw:
            flag = "CONFLICT"
        elif uw >= 2 * mw and uw > 1.0:
            flag = "OVERWEIGHT"
        elif uw == 0 and mw >= 4.0 and m["action"] == "buy":
            flag = "MISSING"
        rows.append((flag, sym, uw, mw, m["action"], m.get("note", "")))
    for sym in sorted(set(user) - set(book)):
        uw = 100.0 * user[sym] / total
        rows.append(("OFF-BOOK", sym, uw, 0.0, "-", "not in mentor book"))

    rows.sort(key=lambda r: (FLAG_ORDER.get(r[0], 9), -r[2]))
    print(f"{'FLAG':<11}{'SYM':<6}{'USER%':>7}{'MENTOR%':>9}  {'M-ACTION':<9} NOTE")
    for flag, sym, uw, mw, act, note in rows:
        if uw == 0 and not flag:
            continue
        print(f"{flag:<11}{sym:<6}{uw:>6.1f}%{mw:>8.1f}%  {act:<9} {note[:60]}")
    n = sum(1 for r in rows if r[0] == "CONFLICT")
    print(f"\n{n} CONFLICT(s). Rules: CONFLICT=resolve or justify in the next report; "
          "OVERWEIGHT=needs the desk's own conviction on record; MISSING=underwrite, don't copy.")


if __name__ == "__main__":
    main()
