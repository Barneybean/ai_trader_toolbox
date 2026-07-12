#!/usr/bin/env python3
"""Append-only mentor position history and change-based learning context."""
import argparse
import datetime as dt
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOTS = os.path.join(ROOT, "journal", "mentor-snapshots")
LIVE = os.path.join(ROOT, "journal", "mentor-book.json")


def load_snapshots():
    rows = []
    if not os.path.isdir(SNAPSHOTS): return rows
    for name in sorted(os.listdir(SNAPSHOTS)):
        if not name.endswith(".json"): continue
        path = os.path.join(SNAPSHOTS, name)
        doc = json.load(open(path, encoding="utf-8"))
        date = doc.get("_meta", {}).get("updated") or name[:-5]
        dt.date.fromisoformat(date)
        rows.append((date, path, doc))
    return rows


def diff_books(old, new):
    before, after = old.get("positions", {}), new.get("positions", {})
    changes = []
    for symbol in sorted(set(before) | set(after)):
        a, b = before.get(symbol), after.get(symbol)
        if a is None: changes.append({"symbol": symbol, "change": "added", "after": b}); continue
        if b is None: changes.append({"symbol": symbol, "change": "removed", "before": a}); continue
        fields = {k: {"from": a.get(k), "to": b.get(k)} for k in ("weight", "action", "target", "note")
                  if a.get(k) != b.get(k)}
        if fields:
            row = {"symbol": symbol, "change": "updated", "fields": fields}
            if a.get("weight") is not None and b.get("weight") is not None:
                row["weight_delta"] = round(float(b["weight"]) - float(a["weight"]), 4)
            changes.append(row)
    return changes


def context(symbol=None):
    snapshots = load_snapshots(); symbol = symbol.upper() if symbol else None
    series = []
    for date, path, doc in snapshots:
        positions = doc.get("positions", {})
        if symbol:
            if symbol in positions: series.append({"date": date, "position": positions[symbol]})
        else:
            series.append({"date": date, "positions": len(positions),
                           "allocated_weight": round(sum(float(x.get("weight") or 0) for x in positions.values()), 2)})
    transitions = []
    for (d1, _, a), (d2, _, b) in zip(snapshots, snapshots[1:]):
        changes = diff_books(a, b)
        if symbol: changes = [x for x in changes if x["symbol"] == symbol]
        if changes: transitions.append({"from": d1, "to": d2, "changes": changes})
    return {"symbol": symbol, "snapshots": series, "transitions": transitions,
            "learning_rule": "Position changes are evidence of evolving conviction, not proof of correctness. Compare later outcomes before promoting a repeated action into a desk rule."}


def add_snapshot(source, date):
    dt.date.fromisoformat(date)
    doc = json.load(open(source, encoding="utf-8"))
    if not isinstance(doc.get("positions"), dict): raise SystemExit("snapshot needs a positions object")
    doc.setdefault("_meta", {})["updated"] = date
    os.makedirs(SNAPSHOTS, exist_ok=True)
    dst = os.path.join(SNAPSHOTS, date + ".json")
    if os.path.exists(dst): raise SystemExit(f"refusing to overwrite historical snapshot: {dst}")
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(doc, f, indent=2, ensure_ascii=False); f.write("\n")
    os.replace(tmp, dst)
    live_tmp = LIVE + ".tmp"; shutil.copyfile(dst, live_tmp); os.replace(live_tmp, LIVE)
    return dst


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("context"); c.add_argument("--symbol")
    d = sub.add_parser("changes"); d.add_argument("--symbol")
    a = sub.add_parser("add"); a.add_argument("snapshot"); a.add_argument("--date", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "list":
        for date, path, doc in load_snapshots(): print(f"{date}  {len(doc.get('positions', {}))} positions  {os.path.relpath(path, ROOT)}")
    elif args.cmd == "context": print(json.dumps(context(args.symbol), indent=2, ensure_ascii=False))
    elif args.cmd == "changes":
        snapshots = load_snapshots()
        if len(snapshots) < 2: return 0
        rows = diff_books(snapshots[-2][2], snapshots[-1][2])
        if args.symbol: rows = [x for x in rows if x["symbol"] == args.symbol.upper()]
        print(json.dumps({"from": snapshots[-2][0], "to": snapshots[-1][0], "changes": rows}, indent=2, ensure_ascii=False))
    else: print(os.path.relpath(add_snapshot(args.snapshot, args.date), ROOT))
    return 0


if __name__ == "__main__": sys.exit(main())
