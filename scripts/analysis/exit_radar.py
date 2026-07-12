#!/usr/bin/env python3
"""Exit radar — time the SELL on a popular / extended winner before it retraces.

Popular stocks run further than fair value says they should; the money is made
by riding the run AND leaving before the give-back. This scores the
distribution tells and prints a concrete stop ladder, so the exit is a
pre-committed level, not a mood.

    python3 scripts/analysis/exit_radar.py NVDA                     # Yahoo 2y daily
    python3 scripts/analysis/exit_radar.py MU --entry 150           # + give-back guard
    python3 scripts/analysis/exit_radar.py bars.json --entry 42.2   # connector bars file
    python3 scripts/analysis/exit_radar.py NVDA --float 2.3e10 --json

Tells (each 0-25, total = exit tension 0-100+):
  EXTENSION     price stretched >= 6 ATRs above SMA50, at a 90th-pct extreme
  DISTRIBUTION  >=4 down days on above-average volume in the last 25 sessions
  OBV-DIVERGE   price prints a 40d high while OBV can't - buyers thinning
  CLIMAX        a 95th-percentile 5-day burst on >=1.8x volume (blow-off shape)
  SATURATION    >=90% of chips in profit - everyone's a winner, sellers loaded
  GIVE-BACK     already surrendered >=1/3 of the peak gain (needs --entry)

Verdict ladder:
  RIDE     < 25   trend intact - hold, stop stays at the chandelier
  TIGHTEN  25-49  raise the stop to the chandelier level printed; no new adds
  TRIM     50-74  sell 1/4-1/3 INTO STRENGTH (limit above market, not a dump)
  EXIT     >= 75, or a hard break (close below chandelier AND SMA50)

Structure breaks override the score: a close below the chandelier stop and
SMA50 is an EXIT regardless of how few tells fired. The radar times exits on
POPULAR/extended names; a broken thesis exits on the thesis, not the chart.
"""
import argparse
import json
import os
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_SCRIPTS, d) for d in ("lib", "analysis", "ops")]
import indicators  # noqa: E402

CHAND_LOOKBACK = 22
CHAND_MULT = 3.0
DIST_WINDOW = 25
GIVEBACK_MAX = 1 / 3


def _load_bars(source, rng="2y"):
    if os.path.exists(source):
        return indicators._find_bars(json.load(open(source)))
    import yahoo
    return yahoo.fetch(source.upper(), rng=rng)


def _percentile_rank(sorted_vals, x):
    n = len(sorted_vals)
    if n == 0:
        return None
    below = sum(1 for v in sorted_vals if v <= x)
    return 100.0 * below / n


def analyze(bars, entry=None, float_shares=None):
    o, h, l, c, v = indicators._ohlcv(bars)
    if len(c) < 60:
        raise SystemExit("need >=60 daily bars")
    price = c[-1]
    atr = indicators.atr(h, l, c, 14) or 0.0
    sma50 = indicators.sma(c, 50)
    sma200 = indicators.sma(c, 200) if len(c) >= 200 else None

    tells = {}
    score = 0.0

    # Stop ladder ------------------------------------------------------------
    chandelier = max(c[-CHAND_LOOKBACK:]) - CHAND_MULT * (indicators.atr(h, l, c, CHAND_LOOKBACK) or atr)
    ladder = {"chandelier": round(chandelier, 2),
              "sma50": round(sma50, 2) if sma50 else None,
              "sma200": round(sma200, 2) if sma200 else None}

    # 1. EXTENSION — how many ATRs above trend, vs this name's own history
    ext_series = []
    for i in range(49, len(c)):
        s = indicators.sma(c[: i + 1], 50)
        a = indicators.atr(h[: i + 1], l[: i + 1], c[: i + 1], 14)
        if s and a:
            ext_series.append((c[i] - s) / a)
    ext_now = ext_series[-1] if ext_series else 0.0
    ext_pct = _percentile_rank(sorted(ext_series), ext_now) or 0.0
    if ext_now >= 6 and ext_pct >= 90:
        tells["EXTENSION"] = f"{ext_now:.1f} ATRs above SMA50 ({ext_pct:.0f}th pct)"
        score += 25
    elif ext_now >= 4 and ext_pct >= 80:
        tells["EXTENSION"] = f"{ext_now:.1f} ATRs above SMA50 ({ext_pct:.0f}th pct) — building"
        score += 12

    # 2. DISTRIBUTION — institutional selling days in the last 25 sessions
    vol20 = indicators.sma(v, 20) or 0.0
    dist_days = 0
    for i in range(max(1, len(c) - DIST_WINDOW), len(c)):
        if c[i] < c[i - 1] * 0.998 and v[i] > 1.2 * (indicators.sma(v[: i + 1], 20) or vol20):
            dist_days += 1
    if dist_days >= 6:
        tells["DISTRIBUTION"] = f"{dist_days} heavy-volume down days / {DIST_WINDOW}"
        score += 25
    elif dist_days >= 4:
        tells["DISTRIBUTION"] = f"{dist_days} heavy-volume down days / {DIST_WINDOW}"
        score += 15

    # 3. OBV DIVERGENCE — price high the flow refuses to confirm
    obv = indicators.obv_series(c, v)
    obv_hi40 = max(obv[-40:])
    # tolerance as an absolute band so it doesn't flip sign when OBV is negative
    price_hi_recent = max(c[-5:]) >= max(c[-40:]) * 0.999
    obv_hi_recent = max(obv[-5:]) >= obv_hi40 - 0.001 * (abs(obv_hi40) or 1.0)
    if price_hi_recent and not obv_hi_recent:
        tells["OBV-DIVERGE"] = "price at 40d high, OBV is not — buyers thinning"
        score += 20

    # 4. CLIMAX — blow-off velocity on volume
    r5 = [(c[i] / c[i - 5] - 1) for i in range(5, len(c))]
    if r5:
        recent_max = max(r5[-10:])
        if (_percentile_rank(sorted(r5), recent_max) or 0) >= 95 and vol20 > 0 and max(v[-10:]) >= 1.8 * vol20:
            tells["CLIMAX"] = f"5d burst {100*recent_max:.0f}% at 95th+ pct on {max(v[-10:])/vol20:.1f}x volume"
            score += 20

    # 5. SATURATION — everyone in profit = sell fuel
    binned = indicators.chip_bins(h, l, c, v, float_shares=float_shares)
    if binned:
        centers, chips, _w, _pmin = binned
        total = sum(chips)
        in_profit = sum(w for ctr, w in zip(centers, chips) if ctr <= price) / total if total else 0
        if in_profit >= 0.90:
            tells["SATURATION"] = f"{100*in_profit:.0f}% of chips in profit"
            score += 15
    else:
        in_profit = None

    # 6. GIVE-BACK — the retrace guard (the reason this radar exists)
    give_back = None
    if entry:
        peak = max(c)
        peak_gain = peak / entry - 1
        cur_gain = price / entry - 1
        if peak_gain > 0.10:
            give_back = (peak_gain - cur_gain) / peak_gain
            if give_back >= GIVEBACK_MAX:
                tells["GIVE-BACK"] = (f"surrendered {100*give_back:.0f}% of a "
                                      f"{100*peak_gain:.0f}% peak gain")
                score += 25
            elif give_back >= 0.20:
                tells["GIVE-BACK"] = (f"gave back {100*give_back:.0f}% of a "
                                      f"{100*peak_gain:.0f}% peak gain — watch")
                score += 10

    hard_break = price < chandelier and (sma50 is None or price < sma50)
    if hard_break:
        verdict = "EXIT"
    elif score >= 75:
        verdict = "EXIT"
    elif score >= 50:
        verdict = "TRIM"
    elif score >= 25:
        verdict = "TIGHTEN"
    else:
        verdict = "RIDE"

    return {"price": round(price, 2), "verdict": verdict, "exit_tension": round(score),
            "tells": tells, "stop_ladder": ladder, "hard_break": hard_break,
            "extension_atrs": round(ext_now, 1), "distribution_days": dist_days,
            "chips_in_profit_pct": round(100 * in_profit, 1) if in_profit is not None else None,
            "give_back_pct": round(100 * give_back, 1) if give_back is not None else None,
            "entry": entry}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="ticker (Yahoo pull) or bars .json file")
    ap.add_argument("--entry", type=float, help="avg cost — enables the give-back guard")
    ap.add_argument("--float", type=float, dest="float_shares", help="float shares (exact chips)")
    ap.add_argument("--range", default="2y", help="Yahoo range when source is a ticker (default 2y)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = analyze(_load_bars(args.source, args.range), args.entry, args.float_shares)
    if args.json:
        print(json.dumps(res, indent=2))
        return

    name = os.path.basename(args.source).split(".")[0].upper()
    print(f"{name}  price {res['price']}  ->  {res['verdict']}  (exit tension {res['exit_tension']}/100)")
    lad = res["stop_ladder"]
    print(f"  stop ladder: chandelier {lad['chandelier']}  |  SMA50 {lad['sma50']}  |  SMA200 {lad['sma200']}"
          + ("   ** HARD BREAK — below chandelier + SMA50 **" if res["hard_break"] else ""))
    if res["tells"]:
        for k, msg in res["tells"].items():
            print(f"  tell  {k:<13} {msg}")
    else:
        print("  no distribution tells firing")
    print("\n  Playbook: RIDE = hold, stop at chandelier. TIGHTEN = raise stop, no adds."
          "\n            TRIM = scale out INTO STRENGTH (limit above market)."
          "\n            EXIT = structure broke or tension >=75 — sell, don't negotiate."
          "\n  Never round-trip more than 1/3 of the peak gain on a popular-stock ride.")


if __name__ == "__main__":
    main()
