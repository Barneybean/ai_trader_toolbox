#!/usr/bin/env python3
"""Weekly review — assemble everything the desk has said and done into one pack,
so the first run of each week starts from its own history, not a blank page.

The desk's past reports and journals ARE the calibration data: open calls get
marked to market, matured calls get score-ready commands, and the report
archive is indexed for re-reading. The script does the arithmetic; the desk
(LLM) does the judgment — the retrospective protocol lives in
`skills/decision/weekly-retrospective.md`.

    python3 scripts/journal/weekly_review.py                 # human pack
    python3 scripts/journal/weekly_review.py --weeks 4       # archive window (default 4)
    python3 scripts/journal/weekly_review.py --json          # machine pack for the run

Sections:
  OPEN BOOK    every open decision (journal/decisions.jsonl) marked to market:
               since-call return, alpha vs SPY over the same window, distance
               to stop/target, age vs horizon; STOP-BREACHED flags loud.
  MATURED      open calls past their horizon (or stop-breached) with the exact
               `track_record.py score` command pre-filled — score, then reflect.
  INSIGHTS     score_insights.py --mark pass-through: per-method hit table +
               open insights marked; expired-unscored flagged.
  LEVELS       check_alerts.py pass-through: triggered / expiring action levels.
  ARCHIVE      reports/**/*.html indexed by date — the re-read list for the window
               (every report carries calls, catalyst maps, and two-horizon
               clocks that don't expire just because the file scrolled by).
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_SCRIPTS, d) for d in ("lib", "analysis", "ops")]
import yahoo  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DECISIONS = os.path.join(ROOT, "journal", "decisions.jsonl")
REPORTS = os.path.join(ROOT, "reports")

HORIZON_DAYS = {"d": 1, "wk": 7, "w": 7, "mo": 30, "m": 30, "y": 365, "yr": 365}


def _today():
    # last bar date is the market clock; fall back to system date offline
    try:
        return dt.date.fromisoformat(_price_series("SPY")[-1][0])
    except Exception:
        return dt.date.today()


_series_cache = {}


_fetch_rng = "6mo"


def _pick_range(oldest_iso, today):
    """Fetch window must contain the oldest open call's date, or the baseline
    close silently becomes the window-start bar (wrong return, wrong alpha)."""
    if not oldest_iso:
        return "6mo"
    age = (today - dt.date.fromisoformat(oldest_iso)).days
    for days, rng in ((150, "6mo"), (330, "1y"), (700, "2y")):
        if age <= days:
            return rng
    return "5y"


def _price_series(tkr):
    """[(iso_date, close), ...] daily over the run's chosen window, cached."""
    if tkr not in _series_cache:
        bars = yahoo.fetch(tkr, rng=_fetch_rng)
        _series_cache[tkr] = [(b["begins_at"][:10], float(b["close"]))
                              for b in bars if b.get("close")]
    return _series_cache[tkr]


def _close_on_or_after(series, iso):
    for d, c in series:
        if d >= iso:
            return c
    return None


def _horizon_days(h):
    """Parse '3mo', '2wk', and RANGE forms like '6-18mo' / '2-6wk' (use the
    upper bound — a call isn't matured until its full window lapsed)."""
    if not h:
        return None
    m = re.match(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*([a-z]+)", str(h).lower())
    if not m:
        return None
    qty = float(m.group(2) or m.group(1))
    unit = m.group(3)
    for k, days in HORIZON_DAYS.items():
        if unit.startswith(k):
            return qty * days
    return None


def open_book(today):
    from jsonl import load_jsonl
    global _fetch_rng
    rows = []
    decisions = [r for r in load_jsonl(DECISIONS) if r.get("status") == "open"]
    if not decisions:
        return rows
    dated = [r["date"] for r in decisions if r.get("date")]
    chosen_range = _pick_range(min(dated) if dated else None, today)
    if chosen_range != _fetch_rng:
        _fetch_rng = chosen_range
        _series_cache.clear()  # _today() may have cached a shorter SPY series
    try:
        spy = _price_series("SPY")
    except Exception as e:
        # offline: still emit the book so the pack survives — just unmarked
        return [{**{k: r.get(k) for k in ("id", "symbol", "date", "action",
                "entry", "stop", "target", "horizon", "conviction")},
                 "error": f"no market data ({e})"} for r in decisions]
    for r in decisions:
        sym, date = r["symbol"], r["date"]
        try:
            series = _price_series(sym)
            price = series[-1][1]
            base = _close_on_or_after(series, date)
        except Exception:
            rows.append({**{k: r.get(k) for k in ("id", "symbol", "date", "action",
                        "entry", "stop", "target", "horizon", "conviction")},
                         "error": "no price data"})
            continue
        ret = price / base - 1 if base else None
        spy_base = _close_on_or_after(spy, date)
        spy_ret = (spy[-1][1] / spy_base - 1) if spy_base else None
        age = (today - dt.date.fromisoformat(date)).days
        hdays = _horizon_days(r.get("horizon"))
        stop, target = r.get("stop"), r.get("target")
        # a trim/avoid/sell call WORKS when the price falls — grade on the call's own side
        bearish = str(r.get("action", "")).lower() in (
            "trim", "avoid", "sell", "sell-all", "exit", "veto", "underweight")
        call_ret = (-ret if (bearish and ret is not None) else ret)
        # alpha on the call's side too, or the columns contradict each other
        alpha = ((call_ret + spy_ret) if bearish else (call_ret - spy_ret)) \
            if (call_ret is not None and spy_ret is not None) else None
        flag = "ON-TRACK"
        if not bearish and stop and price <= stop:
            flag = "STOP-BREACHED"
        elif bearish and stop and r.get("entry") and stop > r["entry"] and price >= stop:
            flag = "STOP-BREACHED"       # bearish invalidation = price rallying through it
        elif not bearish and target and price >= target:
            flag = "TARGET-HIT"
        elif bearish and target and r.get("entry") and target < r["entry"] and price <= target:
            flag = "TARGET-HIT"          # fall-to target (below entry) reached
        elif bearish and target and r.get("entry") and target > r["entry"] and price >= target:
            flag = "TARGET-HIT"          # sell-into-strength level (above entry) reached
        elif hdays and age >= hdays:
            flag = "MATURED"
        elif call_ret is not None and call_ret < -0.10:
            flag = "LAGGING"
        rows.append({"id": r["id"], "symbol": sym, "date": date, "action": r.get("action"),
                     "sleeve": r.get("sleeve"), "entry": r.get("entry"), "stop": stop,
                     "target": target, "horizon": r.get("horizon"), "age_days": age,
                     "price": round(price, 2), "since_call_pct": round(100 * ret, 1) if ret is not None else None,
                     "call_working_pct": round(100 * call_ret, 1) if call_ret is not None else None,
                     "alpha_pct": round(100 * alpha, 1) if alpha is not None else None,
                     "side": "bearish" if bearish else "long",
                     "flag": flag,
                     "score_cmd": (f"python3 scripts/journal/track_record.py score --id {r['id']} "
                                   f"--exit {price:.2f}"
                                   + (f" --spy-entry {spy_base:.2f} --spy-exit {spy[-1][1]:.2f}"
                                      if spy_base else "")
                                   if flag in ("MATURED", "STOP-BREACHED", "TARGET-HIT") else None)})
    return rows


def archive_index(weeks, today):
    idx = []
    cutoff = today - dt.timedelta(weeks=weeks)
    files = []
    for folder, dirs, names in os.walk(REPORTS):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("charts", "data")]
        files.extend((folder, f) for f in names if f.endswith(".html"))
    for folder, f in sorted(files):
        m = re.match(r"report_(\d{4}-\d{2}-\d{2})_(.+?)_(.+?)\.html$", f)
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        rel = os.path.relpath(os.path.join(folder, f), ROOT)
        idx.append({"file": rel, "date": m.group(1), "title": m.group(2),
                    "in_window": d >= cutoff})
    return idx


def _sub_json(script, *flags):
    try:
        out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "journal", script),
                              *flags], capture_output=True, text=True, timeout=120)
        return json.loads(out.stdout) if out.stdout.strip() else {"error": out.stderr[:200]}
    except Exception as e:
        return {"error": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weeks", type=int, default=4, help="archive re-read window (default 4)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    today = _today()
    pack = {"asof": today.isoformat(),
            "open_book": open_book(today),
            "insights": _sub_json("score_insights.py", "--mark", "--json"),
            "levels": _sub_json("check_alerts.py", "--json"),
            "archive": archive_index(args.weeks, today)}

    if args.json:
        print(json.dumps(pack, indent=2))
        return

    print(f"# Weekly review pack — as of {pack['asof']}\n")
    print("## OPEN BOOK (decisions marked to market)")
    if not pack["open_book"]:
        print("  (no open decisions)")
    for r in pack["open_book"]:
        if r.get("error"):
            print(f"  ?? {r['id']}: {r['error']}")
            continue
        work = f"{r['call_working_pct']:+.1f}%" if r.get("call_working_pct") is not None else "--"
        alpha = f"{r['alpha_pct']:+.1f}%" if r["alpha_pct"] is not None else "--"
        side = "v" if r.get("side") == "bearish" else " "
        print(f"  {r['flag']:<14} {r['symbol']:<5} {str(r['action']):<10}{side} {r['date']}  "
              f"px {r['price']:>8}  call {work:>7}  alpha {alpha:>7}  "
              f"age {r['age_days']}d/{r['horizon']}")
        if r.get("score_cmd"):
            print(f"      -> {r['score_cmd']}")
    matured = [r for r in pack["open_book"] if r.get("score_cmd")]
    print(f"\n  {len(matured)} call(s) ready to SCORE (then `reflect` one lesson each).")

    ins = pack["insights"]
    if isinstance(ins, list):
        open_n = sum(1 for i in ins if str(i.get("status", "")).startswith("open"))
        scored = [i for i in ins if i.get("hit") is not None and not str(i.get("status", "")).startswith("open")]
        hits = sum(1 for i in scored if i["hit"])
        print(f"\n## INSIGHTS  ({open_n} open marked; {len(scored)} scored, "
              f"{hits}/{len(scored)} hit)" if scored else
              f"\n## INSIGHTS  ({open_n} open, marked to market; none expired yet)")
        meth = {}
        for i in ins:
            for m in i.get("methods", []):
                meth.setdefault(m, []).append(i)
        for m, lst in sorted(meth.items()):
            done = [i for i in lst if i.get("hit") is not None and not str(i.get("status", "")).startswith("open")]
            mk = [i for i in lst if str(i.get("status", "")).startswith("open") and i.get("realized") is not None]
            live = (f"live avg {100*sum(i['realized'] for i in mk)/len(mk):+.1f}%" if mk else "")
            hit = f"{sum(1 for i in done if i['hit'])}/{len(done)} hit" if done else "unscored"
            print(f"    {m:<22} n={len(lst):<3} {hit:<10} {live}")
    else:
        print(f"\n## INSIGHTS  unavailable: {ins.get('error')}")

    lev = pack["levels"]
    if isinstance(lev, list):
        trig = [x for x in lev if str(x.get("status", "")).upper().startswith("TRIG")]
        print(f"\n## LEVELS  {len(trig)} triggered / {len(lev)} registered (full table: scripts/journal/check_alerts.py)")
        for x in trig:
            print(f"    TRIGGERED {x.get('ticker'):<5} {x.get('direction')} {x.get('level')}  {str(x.get('action'))[:70]}")
    else:
        print(f"\n## LEVELS  unavailable: {lev.get('error')}")

    print(f"\n## ARCHIVE — re-read window: {args.weeks} week(s)")
    for a in pack["archive"]:
        mark = "READ ->" if a["in_window"] else "       "
        print(f"    {mark} {a['date']}  {a['title']}")
    print("\nProtocol: skills/decision/weekly-retrospective.md — continuity board, scoring,"
          "\nthen calibration (>=2 same-mode misses before any toolkit threshold moves).")


if __name__ == "__main__":
    import desk_log
    raise SystemExit(desk_log.run(main))
