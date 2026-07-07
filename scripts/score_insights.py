#!/usr/bin/env python3
"""Score the desk's insight registry against realized prices (LEAN-style feedback loop).

Registry: journal/insights.jsonl — one JSON object per line:
  {"id": "xyz-long-20260705", "ts": "2026-07-05", "ticker": "XYZ",
   "direction": "up",              # up | down | flat
   "magnitude": 0.30,              # expected move in direction, decimal (0.30 = +30%)
   "confidence": 0.60,             # 0-1
   "price_at_call": 100.00,
   "expires": "2027-07-05",
   "methods": ["layer-rotation", "chip-distribution"],   # generating method tags
   "thesis": "xyz-theme-definer",                        # GroupId linking horizons
   "source": "report_<date>_<title>",
   "cancelled": false}             # set true when a stop fires / thesis breaks

Scoring (only on expiry, or --mark for open mark-to-market):
  direction hit: up -> realized > +2%; down -> realized < -2%; flat -> |realized| <= 5%
  magnitude error: |realized - signed expected| (reported for hits and misses)
Aggregates are reported PER METHOD TAG — the point is to learn which desk
method actually hits, not just the blended average.

Usage:
  python3 scripts/score_insights.py          # score expired insights
  python3 scripts/score_insights.py --mark   # also mark-to-market open ones
  python3 scripts/score_insights.py --json
"""
import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yahoo  # noqa: E402

REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "journal", "insights.jsonl")


def load(path):
    recs = []
    if not os.path.exists(path):
        return recs
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"warn: bad JSON line {n}: {e}", file=sys.stderr)
    return recs


def realized_return(rec, bars):
    """Return (asof_date, realized_pct, expired) using close on/last before expiry."""
    px0 = float(rec["price_at_call"])
    expiry = rec.get("expires", "9999-12-31")
    upto = [b for b in bars if b["begins_at"] >= rec["ts"]]
    if not upto:
        return None
    latest = upto[-1]
    expired = latest["begins_at"] >= expiry
    if expired:
        at = [b for b in upto if b["begins_at"] <= expiry]
        bar = at[-1] if at else latest
    else:
        bar = latest
    return bar["begins_at"], (bar["close"] - px0) / px0, expired


def direction_hit(direction, ret):
    if direction == "up":
        return ret > 0.02
    if direction == "down":
        return ret < -0.02
    return abs(ret) <= 0.05  # flat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark", action="store_true", help="also mark-to-market open insights")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--registry", default=REGISTRY)
    args = ap.parse_args()

    recs = load(args.registry)
    if not recs:
        print(f"no insights registered ({args.registry})")
        return 0

    bars_cache = {}
    rows = []
    for rec in recs:
        if rec.get("cancelled"):
            rows.append({**rec, "status": "CANCELLED"})
            continue
        t = rec["ticker"].upper()
        if t not in bars_cache:
            try:
                bars_cache[t] = yahoo.fetch(t, rng="2y", interval="1d")
            except Exception as e:
                bars_cache[t] = e
        bars = bars_cache[t]
        if isinstance(bars, Exception):
            rows.append({**rec, "status": "ERROR", "detail": str(bars)})
            continue
        rr = realized_return(rec, bars)
        if rr is None:
            rows.append({**rec, "status": "open (no bars since call yet)"})
            continue
        asof, ret, expired = rr
        if not expired and not args.mark:
            rows.append({**rec, "status": "open"})
            continue
        signed_exp = {"up": 1, "down": -1, "flat": 0}[rec["direction"]] * float(rec.get("magnitude", 0))
        rows.append({
            **rec,
            "status": "SCORED" if expired else "open (marked)",
            "asof": asof,
            "realized": round(ret, 4),
            "expected": round(signed_exp, 4),
            "hit": direction_hit(rec["direction"], ret),
            "mag_error": round(abs(ret - signed_exp), 4),
        })

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    scored = [r for r in rows if r["status"].startswith(("SCORED", "open (marked)"))]
    print(f"{'ID':<28} {'STATUS':<15} {'DIR':<5} {'CONF':>4} {'EXP%':>7} {'REAL%':>7} {'HIT':<4} METHODS")
    for r in rows:
        if "realized" in r:
            print(f"{r['id']:<28} {r['status']:<15} {r['direction']:<5} {r['confidence']:>4.2f} "
                  f"{r['expected']*100:>+6.1f}% {r['realized']*100:>+6.1f}% "
                  f"{'✓' if r['hit'] else '✗':<4} {','.join(r.get('methods', []))}")
        else:
            print(f"{r['id']:<28} {r['status']:<15} {r['direction']:<5} "
                  f"{r.get('confidence', 0):>4.2f} {'':>7} {'':>7} {'':<4} "
                  f"{','.join(r.get('methods', []))}")

    if scored:
        by_method = defaultdict(list)
        for r in scored:
            for m in r.get("methods", ["untagged"]):
                by_method[m].append(r)
        print("\nPER-METHOD (scored + marked):")
        for m, rs in sorted(by_method.items()):
            hits = sum(1 for r in rs if r["hit"])
            avg_err = sum(r["mag_error"] for r in rs) / len(rs)
            print(f"  {m:<22} n={len(rs):<3} hit-rate {hits/len(rs)*100:.0f}%  avg |mag err| {avg_err*100:.1f}%")
        n_exp = sum(1 for r in scored if r["status"] == "SCORED")
        print(f"\n{n_exp} expired-scored / {len(scored)} evaluated / {len(rows)} registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
