#!/usr/bin/env python3
"""Check the desk's action-price levels registry against live market data.

Registry: journal/action-levels.jsonl — one JSON object per line:
  {"ticker": "SYM", "level": 43.0, "direction": "below",
   "action": "BUY starter, zone 40-43", "source": "report_2026-07-05_ai-robotics-value-chain",
   "set": "2026-07-05", "expires": "2026-10-05", "account": "joint",
   "not_before": "2026-08-06"}          # not_before optional (e.g. wash-sale windows)

direction "below": triggers when any daily LOW since `set` is <= level.
direction "above": triggers when any daily HIGH since `set` is >= level.
Intraday touches count — bottoms/breakouts rarely wait for the close.

Usage:
  python3 scripts/journal/check_alerts.py           # human table
  python3 scripts/journal/check_alerts.py --json    # machine-readable
Data source: scripts/lib/yahoo.py (no broker login needed; ~15min delayed is fine
for a between-runs sweep — the desk re-verifies with live quotes before acting).
"""
import argparse
import datetime as dt
import json
import os
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_SCRIPTS, d) for d in ("lib", "analysis", "ops")]
import yahoo  # noqa: E402

REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "journal", "action-levels.jsonl")


def load_levels(path):
    levels = []
    if not os.path.exists(path):
        return levels
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
                rec["_line"] = n
                levels.append(rec)
            except json.JSONDecodeError as e:
                print(f"warn: bad JSON on line {n}: {e}", file=sys.stderr)
    return levels


def _pick_range(levels):
    """The bar window must reach back to the oldest `set` date, or a level that
    triggered months ago silently reports 'armed'."""
    sets = [r.get("set") for r in levels if r.get("set")]
    if not sets:
        return "3mo"
    oldest = min(sets)
    try:
        age = (dt.date.today() - dt.date.fromisoformat(oldest)).days
    except ValueError:
        return "1y"
    for days, rng in ((80, "3mo"), (170, "6mo"), (350, "1y")):
        if age <= days:
            return rng
    return "2y"


def check(levels):
    out = []
    bars_cache = {}
    rng = _pick_range(levels)
    for rec in levels:
        row = dict(rec)
        try:
            t = rec["ticker"].upper()
            lvl = float(rec["level"])
            direction = rec["direction"]
            if direction not in ("above", "below"):
                raise ValueError("direction must be 'above' or 'below'")
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            row["status"] = "ERROR"
            row["detail"] = f"invalid registry row: {e}"
            out.append(row)
            continue
        if t not in bars_cache:
            try:
                bars_cache[t] = yahoo.fetch(t, rng=rng, interval="1d")
            except Exception as e:
                bars_cache[t] = e
        bars = bars_cache[t]
        if isinstance(bars, Exception):
            row["status"] = "ERROR"
            row["detail"] = str(bars)
            out.append(row)
            continue
        if not bars:
            row["status"] = "ERROR"
            row["detail"] = "no price bars returned"
            out.append(row)
            continue
        since = [b for b in bars if b["begins_at"] >= rec.get("set", "1900-01-01")]
        if not since:
            since = bars[-1:]
        last = bars[-1]
        row["last_close"] = last["close"]
        row["last_date"] = last["begins_at"]
        today = last["begins_at"]  # latest market date, not wall clock
        expired = bool(rec.get("expires") and today > rec["expires"])
        # a trigger that fired while the level was LIVE still matters after expiry
        live = ([b for b in since if b["begins_at"] <= rec["expires"]] if expired else since)
        if expired:
            hits = ([b for b in live if b["low"] <= lvl] if direction == "below"
                    else [b for b in live if b["high"] >= lvl])
            if hits:
                h = hits[0]
                px = h["low"] if rec["direction"] == "below" else h["high"]
                row["status"] = "TRIGGERED (then expired)"
                row["detail"] = f"{px:.2f} on {h['begins_at']} — level has since expired"
            else:
                row["status"] = "EXPIRED"
        elif direction == "below":
            hits = [b for b in since if b["low"] <= lvl]
            if hits:
                h = hits[0]
                row["status"] = "TRIGGERED"
                row["detail"] = f"low {h['low']:.2f} on {h['begins_at']}"
            else:
                row["status"] = "armed"
                row["detail"] = f"{(last['close'] - lvl) / lvl * 100:+.1f}% above level"
        else:  # above
            hits = [b for b in since if b["high"] >= lvl]
            if hits:
                h = hits[0]
                row["status"] = "TRIGGERED"
                row["detail"] = f"high {h['high']:.2f} on {h['begins_at']}"
            else:
                row["status"] = "armed"
                row["detail"] = f"{(lvl - last['close']) / last['close'] * 100:+.1f}% away"
        if row.get("status") == "TRIGGERED" and rec.get("not_before") and today < rec["not_before"]:
            row["status"] = "TRIGGERED (date-gated)"
            row["detail"] += f" — actionable only after {rec['not_before']}"
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--registry", default=REGISTRY)
    args = ap.parse_args()

    levels = load_levels(args.registry)
    if not levels:
        # machine consumers (weekly_review) parse stdout — empty must be [], not prose
        print("[]" if args.json else f"no levels registered ({args.registry})")
        return 0
    rows = check(levels)
    if args.json:
        for r in rows:
            r.pop("_line", None)
        print(json.dumps(rows, indent=2))
        return 0

    order = {"TRIGGERED": 0, "TRIGGERED (date-gated)": 1, "TRIGGERED (then expired)": 2,
             "ERROR": 3, "armed": 4, "EXPIRED": 5}
    rows.sort(key=lambda r: (order.get(r["status"], 9), r["ticker"]))
    w = max(len(r.get("action", "")) for r in rows)
    print(f"{'STATUS':<22} {'TICKER':<7} {'DIR':<6} {'LEVEL':>9} {'LAST':>9}  {'ACTION':<{w}}  DETAIL")
    for r in rows:
        print(f"{r['status']:<22} {r['ticker']:<7} {r['direction']:<6} "
              f"{float(r['level']):>9.2f} {r.get('last_close', float('nan')):>9.2f}  "
              f"{r.get('action', ''):<{w}}  {r.get('detail', '')}")
    n_trig = sum(1 for r in rows if r["status"].startswith("TRIGGERED"))
    print(f"\n{n_trig} triggered / {len(rows)} registered")
    return 0


if __name__ == "__main__":
    import desk_log
    sys.exit(desk_log.run(main))
