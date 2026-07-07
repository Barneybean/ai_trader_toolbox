#!/usr/bin/env python3
"""
Pattern-conditioned price forecaster — quantify the odds of the next move.

Answers the reviewer's question: "it's testing support N times and the band is
narrowing — what's the chance it breaks up vs down, and by how much?" It does
that three ways, from the *data*, not from a hunch:

  1) STRUCTURE  — find the support/resistance being tested, count the touches,
     measure the Bollinger squeeze (band width vs its own history → a percentile).
     Repeated tests of one level and a tight band are the setup; this quantifies
     how tight and how tested.

  2) HISTORICAL ANALOGS — scan this symbol's own history (and any other series
     you pass) for past bars in the SAME state (band squeezed into its lower
     tercile AND price sitting on a multi-touch support), then measure what
     actually happened next: the forward-return distribution, and how often it
     broke up vs down. An empirical base rate, not a rule of thumb.

  3) MONTE CARLO — block-bootstrap the daily log-returns (blocks preserve the
     autocorrelation/vol-clustering a squeeze carries) and simulate thousands of
     forward paths. Reports P(up), P(down), first-passage P(hit the breakout
     trigger before the breakdown trigger), the terminal price percentiles, and
     the expected magnitude. A `--drift` knob injects a fundamentals view
     (e.g. a sanction headwind) as an annualized drift so you can see the setup
     both "chart-only" and "chart + view".

Pure standard library. Deterministic (seeded) so a report is reproducible.

Usage:
  python3 scripts/forecast.py MP.json --price 53.48 --horizon 20 --sims 20000
  python3 scripts/forecast.py MP.json --price 53.48 --drift -0.15        # -15%/yr view
  python3 scripts/forecast.py MP.json --peers NVDA.json,TSLA.json        # add analog pool
  python3 scripts/forecast.py MP.json --json                             # machine-readable
"""

import argparse
import json
import math
import os
import random
import re
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import indicators as ind  # noqa: E402  (reuse the shared bar parser)

SEED = 20260705


# ----------------------------------------------------------------------------- data
def load_bars(source, rng="5y"):
    """Load OHLCV from either a historicals JSON file/'-'/stdin, OR — when `source`
    is a bare ticker with no matching file — fetch multi-year daily bars from Yahoo
    Finance (see scripts/yahoo.py). Yahoo gives far more history than the Robinhood
    connector's ~1y, which sharpens the base rates and the Monte-Carlo bootstrap."""
    if _looks_like_ticker(source):
        import yahoo  # local, stdlib-only fetcher
        bars = yahoo.fetch(source, rng=rng, interval="1d", adjusted=True)
        return ind._ohlcv(bars)
    raw = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
    raw = json.loads(raw)
    if isinstance(raw, dict):
        raw = raw.get("bars") or raw.get("results") or raw.get("historicals") or raw
    o, h, l, c, v = ind._ohlcv(ind._find_bars(raw))
    return o, h, l, c, v


def _looks_like_ticker(source):
    """A ticker (fetch from Yahoo) vs. a path/stdin (read a file). A 1–6 char
    all-caps symbol that is NOT an existing file is treated as a ticker."""
    import os
    s = str(source).strip()
    if s == "-" or os.path.exists(s):
        return False
    return bool(re.fullmatch(r"[A-Z][A-Z.\-]{0,5}", s))


def log_returns(closes):
    return [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
            if closes[i - 1] > 0 and closes[i] > 0]


# ------------------------------------------------------------------- 1) structure
def bollinger_width_series(closes, n=20, k=2.0):
    """%-width of the Bollinger band at each bar (upper-lower)/mid * 100."""
    out = []
    for i in range(len(closes)):
        if i < n - 1:
            out.append(None); continue
        w = closes[i - n + 1:i + 1]
        m = sum(w) / n
        sd = (sum((x - m) ** 2 for x in w) / n) ** 0.5
        out.append((2 * k * sd) / m * 100 if m else None)
    return out


def percentile_rank(series, value):
    vals = [x for x in series if x is not None]
    if not vals:
        return None
    below = sum(1 for x in vals if x <= value)
    return round(100 * below / len(vals), 1)


def find_tested_support(lows, closes, price, lookback=45, tol_pct=2.0):
    """The support being *tested*: the lowest meaningful shelf in the recent
    window, and how many separate bars touched within tol_pct of it."""
    win_lo = lows[-lookback:]
    base = min(win_lo)
    tol = base * tol_pct / 100.0
    # count discrete touches (a touch = a local low within tol of base, not adjacent)
    touches, last = 0, -10
    for i, lo in enumerate(lows[-lookback:]):
        if abs(lo - base) <= tol and i - last > 1:
            touches += 1; last = i
    return round(base, 2), touches, round((price - base) / base * 100, 2)


def find_overhead(highs, price, lookback=45, tol_pct=2.0):
    win = highs[-lookback:]
    top = max(win)
    tol = top * tol_pct / 100.0
    touches, last = 0, -10
    for i, hi in enumerate(win):
        if abs(hi - top) <= tol and i - last > 1:
            touches += 1; last = i
    return round(top, 2), touches, round((top - price) / price * 100, 2)


# --------------------------------------------------------------- 2) hist analogs
def historical_analogs(series_list, horizon=20, squeeze_tercile=0.33,
                       support_win=30, support_tol=3.0):
    """Across every (highs,lows,closes) series, find bars whose state matches the
    setup — band width in its lower `squeeze_tercile` AND price within
    support_tol% of the trailing `support_win` low — and record forward returns."""
    fwd, ups, n = [], 0, 0
    for (h, l, c) in series_list:
        if len(c) < 60 + horizon:
            continue
        widths = bollinger_width_series(c)
        valid = sorted(x for x in widths if x is not None)
        if not valid:
            continue
        thresh = valid[int(len(valid) * squeeze_tercile)]
        for i in range(40, len(c) - horizon):
            w = widths[i]
            if w is None or w > thresh:
                continue
            base = min(l[i - support_win:i + 1])
            if (c[i] - base) / base * 100 > support_tol:
                continue  # not sitting on support
            r = (c[i + horizon] - c[i]) / c[i]
            fwd.append(r); n += 1
            if r > 0:
                ups += 1
    if not fwd:
        return None
    fwd.sort()
    return {
        "episodes": n,
        "p_up": round(100 * ups / n, 1),
        "p_down": round(100 * (n - ups) / n, 1),
        "median_ret_pct": round(100 * fwd[len(fwd) // 2], 2),
        "mean_ret_pct": round(100 * sum(fwd) / n, 2),
        "p10_pct": round(100 * fwd[int(0.10 * n)], 2),
        "p90_pct": round(100 * fwd[int(0.90 * n)], 2),
        "up_avg_pct": round(100 * st.mean([r for r in fwd if r > 0]), 2) if ups else None,
        "down_avg_pct": round(100 * st.mean([r for r in fwd if r <= 0]), 2) if (n - ups) else None,
    }


# ------------------------------------------------------------------ 3) monte carlo
def block_bootstrap_paths(rets, price, horizon, sims, block=5, drift_daily=0.0, rng=None):
    rng = rng or random.Random(SEED)
    paths = []
    n = len(rets)
    for _ in range(sims):
        steps = []
        while len(steps) < horizon:
            start = rng.randrange(0, n - block) if n > block else 0
            steps.extend(rets[start:start + block])
        paths.append([price] + _rebuild_path(price, steps[:horizon], drift_daily))
    return paths


def _rebuild_path(price, steps, drift_daily):
    p, out = price, []
    for r in steps:
        p *= math.exp(r + drift_daily)
        out.append(p)
    return out


def path_percentiles(paths):
    """Per-step price percentiles across all paths → the forecast fan/cone.
    Returns a list (one entry per step incl. step 0) of p10/p25/median/p75/p90."""
    H = len(paths[0])
    out = []
    for step in range(H):
        col = sorted(p[step] for p in paths)
        n = len(col)
        q = lambda f: col[min(n - 1, int(f * n))]  # noqa: E731
        out.append({"p10": round(q(0.10), 2), "p25": round(q(0.25), 2),
                    "median": round(q(0.50), 2), "p75": round(q(0.75), 2),
                    "p90": round(q(0.90), 2)})
    return out


def cone(closes, price, horizon=20, sims=20000, drift_annual=0.0, block=5):
    """The forecast fan for charting: block-bootstrap forward paths from the recent
    return regime and reduce to per-step percentiles. Pure function of the closes."""
    rets = log_returns(closes)
    recent = rets[-60:] if len(rets) > 60 else rets
    drift_daily = math.log(1 + drift_annual) / 252 if drift_annual else 0.0
    paths = block_bootstrap_paths(recent, price, horizon, sims, block=block,
                                  drift_daily=drift_daily, rng=random.Random(SEED))
    return path_percentiles(paths)


def summarize_paths(paths, price, up_trigger, dn_trigger):
    terminal = sorted(p[-1] for p in paths)
    n = len(terminal)
    up = sum(1 for t in terminal if t > price)
    hit_up = hit_dn = first_up = first_dn = 0
    for p in paths:
        tu = td = None
        for i, x in enumerate(p):
            if tu is None and x >= up_trigger:
                tu = i
            if td is None and x <= dn_trigger:
                td = i
        if tu is not None:
            hit_up += 1
        if td is not None:
            hit_dn += 1
        if tu is not None and (td is None or tu < td):
            first_up += 1
        elif td is not None:
            first_dn += 1
    q = lambda f: round(terminal[int(f * n)], 2)  # noqa: E731
    return {
        "p_up": round(100 * up / n, 1),
        "p_down": round(100 * (n - up) / n, 1),
        "terminal_median": q(0.50),
        "terminal_p10": q(0.10),
        "terminal_p25": q(0.25),
        "terminal_p75": q(0.75),
        "terminal_p90": q(0.90),
        "exp_move_pct": round(100 * (sum(terminal) / n - price) / price, 2),
        "median_move_pct": round(100 * (q(0.50) - price) / price, 2),
        "p_touch_breakout": round(100 * hit_up / n, 1),
        "p_touch_breakdown": round(100 * hit_dn / n, 1),
        "p_breakout_first": round(100 * first_up / n, 1),
        "p_breakdown_first": round(100 * first_dn / n, 1),
    }


# ------------------------------------------------------------------------- driver
def build(o, h, l, c, v, price, horizon, sims, drift_annual, up_trigger, dn_trigger,
          peers=None):
    rets = log_returns(c)
    recent = rets[-60:] if len(rets) > 60 else rets
    ann_vol = st.pstdev(rets) * math.sqrt(252) if len(rets) > 2 else None
    widths = bollinger_width_series(c)
    cur_w = next((x for x in reversed(widths) if x is not None), None)
    sup, sup_t, sup_d = find_tested_support(l, c, price)
    res, res_t, res_d = find_overhead(h, price)
    up_trigger = up_trigger or res
    dn_trigger = dn_trigger or round(sup * 0.985, 2)  # just under the tested shelf

    analog_pool = [(h, l, c)] + (peers or [])
    analogs = historical_analogs(analog_pool, horizon=horizon)

    drift_daily = math.log(1 + drift_annual) / 252 if drift_annual else 0.0
    rng = random.Random(SEED)
    paths_chart = block_bootstrap_paths(recent, price, horizon, sims, drift_daily=0.0, rng=rng)
    mc_chart = summarize_paths(paths_chart, price, up_trigger, dn_trigger)
    mc_view = None
    if drift_annual:
        rng2 = random.Random(SEED)
        paths_view = block_bootstrap_paths(recent, price, horizon, sims,
                                           drift_daily=drift_daily, rng=rng2)
        mc_view = summarize_paths(paths_view, price, up_trigger, dn_trigger)

    return {
        "price": price, "horizon_days": horizon, "sims": sims,
        "ann_vol_pct": round(100 * ann_vol, 1) if ann_vol else None,
        "squeeze": {
            "bb_width_pct": round(cur_w, 2) if cur_w else None,
            "width_percentile": percentile_rank(widths, cur_w),
            "is_squeeze": (percentile_rank(widths, cur_w) or 100) <= 33,
        },
        "support": {"level": sup, "touches": sup_t, "dist_pct": sup_d},
        "overhead": {"level": res, "touches": res_t, "dist_pct": res_d},
        "triggers": {"breakout_above": up_trigger, "breakdown_below": dn_trigger},
        "historical_analogs": analogs,
        "monte_carlo_chart_only": mc_chart,
        "drift_annual": drift_annual,
        "monte_carlo_with_view": mc_view,
    }


def _fmt(r):
    L = []
    p = r["price"]
    L.append(f"  price ${p}  ·  {r['horizon_days']}d horizon  ·  {r['sims']:,} sims  ·  ann-vol {r['ann_vol_pct']}%")
    sq = r["squeeze"]
    L.append(f"\nSTRUCTURE")
    L.append(f"  Bollinger width {sq['bb_width_pct']}%  →  {sq['width_percentile']}th percentile of its own history"
             f"  ({'SQUEEZE (coiled)' if sq['is_squeeze'] else 'not squeezed'})")
    s, ov = r["support"], r["overhead"]
    L.append(f"  Support tested  ${s['level']}  ·  {s['touches']} touches  ·  {s['dist_pct']:+}% away")
    L.append(f"  Overhead        ${ov['level']}  ·  {ov['touches']} touches  ·  {ov['dist_pct']:+}% away")
    t = r["triggers"]
    L.append(f"  Triggers: breakout > ${t['breakout_above']} | breakdown < ${t['breakdown_below']}")
    a = r["historical_analogs"]
    L.append(f"\nHISTORICAL ANALOGS  (squeeze + on-support states, {r['horizon_days']}d forward)")
    if a:
        L.append(f"  {a['episodes']} past episodes  →  UP {a['p_up']}% / DOWN {a['p_down']}%")
        L.append(f"  forward return: median {a['median_ret_pct']:+}%  mean {a['mean_ret_pct']:+}%"
                 f"  (p10 {a['p10_pct']:+}% … p90 {a['p90_pct']:+}%)")
        ua = f"{a['up_avg_pct']:+}%" if a['up_avg_pct'] is not None else "n/a"
        da = f"{a['down_avg_pct']:+}%" if a['down_avg_pct'] is not None else "n/a"
        L.append(f"  when up, avg {ua}  ·  when down, avg {da}")
    else:
        L.append("  (too few matching episodes in the pool)")
    m = r["monte_carlo_chart_only"]
    L.append(f"\nMONTE CARLO — chart only (no view)")
    L.append(f"  P(up) {m['p_up']}%  /  P(down) {m['p_down']}%   ·   expected {m['exp_move_pct']:+}%  median {m['median_move_pct']:+}%")
    L.append(f"  terminal price: p10 ${m['terminal_p10']}  median ${m['terminal_median']}  p90 ${m['terminal_p90']}")
    L.append(f"  first-passage: breakout-first {m['p_breakout_first']}%  vs  breakdown-first {m['p_breakdown_first']}%")
    L.append(f"  (ever touch: up {m['p_touch_breakout']}% / down {m['p_touch_breakdown']}%)")
    if r["monte_carlo_with_view"]:
        mv = r["monte_carlo_with_view"]
        L.append(f"\nMONTE CARLO — with view (drift {r['drift_annual']:+.0%}/yr)")
        L.append(f"  P(up) {mv['p_up']}%  /  P(down) {mv['p_down']}%   ·   expected {mv['exp_move_pct']:+}%  median {mv['median_move_pct']:+}%")
        L.append(f"  terminal price: p10 ${mv['terminal_p10']}  median ${mv['terminal_median']}  p90 ${mv['terminal_p90']}")
        L.append(f"  first-passage: breakout-first {mv['p_breakout_first']}%  vs  breakdown-first {mv['p_breakdown_first']}%")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description="Pattern-conditioned price forecaster.")
    p.add_argument("source")
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--horizon", type=int, default=20, help="trading days forward")
    p.add_argument("--sims", type=int, default=20000)
    p.add_argument("--drift", type=float, default=0.0, help="annualized fundamentals drift, e.g. -0.15")
    p.add_argument("--breakout", type=float, default=None)
    p.add_argument("--breakdown", type=float, default=None)
    p.add_argument("--peers", default=None,
                   help="comma list of analog-pool sources — each a historicals JSON path OR a bare ticker")
    p.add_argument("--range", default="5y",
                   help="Yahoo history window when source/peer is a ticker (default 5y)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    o, h, l, c, v = load_bars(a.source, a.range)
    price = a.price or c[-1]
    peers = []
    if a.peers:
        for pth in a.peers.split(","):
            po, ph, pl, pc, pv = load_bars(pth.strip(), a.range)
            peers.append((ph, pl, pc))
    r = build(o, h, l, c, v, price, a.horizon, a.sims, a.drift,
              a.breakout, a.breakdown, peers=peers)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        sym = os.path.splitext(os.path.basename(a.source))[0]
        print(f"=== {sym} — pattern forecast ===")
        print(_fmt(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
