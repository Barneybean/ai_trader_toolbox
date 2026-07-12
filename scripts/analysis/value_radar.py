#!/usr/bin/env python3
"""Value radar — find names whose *fair value* sits >=30% above price, then gate
the entry on technical wash-confirmation so cheap doesn't mean falling knife.

The desk (LLM) gathers the inputs from primary sources (filings, connector
fundamentals) with citations; this script only applies the math — no data
invention. Price/bars auto-pull from Yahoo (scripts/lib/yahoo.py) when omitted.

Fair value is triangulated from up to three independent legs (median wins,
>=2 legs required — one model can always be argued into any answer):
  A. owner-earnings DCF   — PV of the desk's *underwritten* growth (reverse_dcf
                            engine); also reports the growth the price implies.
  B. mature comparable    — normalized EPS x a mature peer multiple.
  C. historical reversion — normalized EPS x the stock's own 5y multiple band.
Optional bear floor       — bear EPS x bear multiple -> the downside check.

Verdicts: DEEP_VALUE (>=50% upside) / VALUE_30 (>=30%) / FAIR / RICH.
Entry gate (from bars): WASHED (>=20% off 52wk high) + BASING (OBV accumulating
or price reclaiming SMA50) -> BUY-CANDIDATE; washed but still knifing -> WAIT.

    python3 scripts/analysis/value_radar.py --metrics candidates.json [--json]

candidates.json: [{"ticker": "XYZ",
    "eps_norm": 2.10,          # normalized EPS (desk's judgment, cited)
    "mature_pe": 22,           # leg B: mature-comparable multiple
    "hist_pe_low": 14, "hist_pe_high": 30,   # leg C: own 5y band
    "fcf": 4.1e9, "shares": 1.48e9, "growth": 0.08,   # leg A (all three)
    "eps_bear": 1.60, "pe_bear": 12,          # optional bear floor
    "price": 43.21,            # optional; Yahoo last close if omitted
    "discount": 0.10, "terminal": 0.025, "years": 10,  # leg A overrides
    "note": "why it's on the radar"}, ...]

Every input is the desk's to defend — the radar turns judgments into a
ranked, falsifiable screen; it does not manufacture the judgments.
"""
import argparse
import json
import os
import statistics
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_SCRIPTS, d) for d in ("lib", "analysis", "ops")]
import indicators  # noqa: E402
from reverse_dcf import implied_growth, pv_of_growth  # noqa: E402

WASH_OFF_HIGH = 0.20     # >=20% off the 52wk high = washed territory
UPSIDE_BUY = 0.30        # the ">=30% or pass" bar
UPSIDE_DEEP = 0.50
BEAR_FLOOR = -0.20       # bear-case downside worse than -20% kills the entry


def _bars_metrics(ticker):
    """Pull ~1y of daily bars via yahoo.py; return the technical gate inputs."""
    try:
        import yahoo
        bars = yahoo.fetch(ticker, rng="1y")
    except Exception as e:  # offline / bad symbol -> gate runs blind
        return {"error": f"bars unavailable ({e})"}
    o, h, l, c, v = indicators._ohlcv(bars)
    if len(c) < 60:
        return {"error": "not enough history"}
    price = c[-1]
    hi52 = max(c)
    off_high = price / hi52 - 1.0
    sma50 = indicators.sma(c, 50)
    sma200 = indicators.sma(c, 200) if len(c) >= 200 else None
    obv = indicators.obv_series(c, v)
    obv_slope60 = obv[-1] - obv[-60]
    washed = off_high <= -WASH_OFF_HIGH
    basing = obv_slope60 > 0 or (sma50 is not None and price > sma50)
    return {"price": price, "off_52wk_high_pct": round(100 * off_high, 1),
            "above_sma50": bool(sma50 and price > sma50),
            "above_sma200": bool(sma200 and price > sma200),
            "obv_60d": "accumulating" if obv_slope60 > 0 else "distributing",
            "washed": washed, "basing": basing}


def _has(m, *keys):
    """Keys present AND non-null — a candidate JSON with explicit nulls must
    degrade to NEED_2_LEGS, not crash the sweep."""
    return all(m.get(k) is not None for k in keys)


def evaluate(m):
    t = m["ticker"].upper()
    tech = _bars_metrics(t)
    price = m.get("price") or tech.get("price")
    out = {"ticker": t, "price": price, "note": m.get("note", ""), "legs": {}, "tech": tech}
    if not price:
        out["verdict"] = "NO_PRICE"
        return out

    r = m.get("discount", 0.10)
    gt = m.get("terminal", 0.025)
    yrs = m.get("years", 10)

    # Leg A — owner-earnings DCF at the desk's underwritten growth
    if _has(m, "fcf", "shares", "growth") and m["shares"] > 0:
        fair_ps = pv_of_growth(m["fcf"], m["growth"], r, gt, yrs) / m["shares"]
        out["legs"]["dcf"] = round(fair_ps, 2)
        out["implied_growth_pct"] = round(
            100 * implied_growth(price * m["shares"], m["fcf"], r, gt, yrs), 1)
        out["underwritten_growth_pct"] = round(100 * m["growth"], 1)

    # Leg B — mature-comparable multiple on normalized EPS
    if _has(m, "eps_norm", "mature_pe"):
        out["legs"]["comparable"] = round(m["eps_norm"] * m["mature_pe"], 2)

    # Leg C — reversion to the stock's own historical multiple band (midpoint)
    if _has(m, "eps_norm", "hist_pe_low", "hist_pe_high"):
        mid = (m["hist_pe_low"] + m["hist_pe_high"]) / 2.0
        out["legs"]["hist_band"] = round(m["eps_norm"] * mid, 2)

    if len(out["legs"]) < 2:
        out["verdict"] = "NEED_2_LEGS"
        return out

    fair = statistics.median(out["legs"].values())
    upside = fair / price - 1.0
    out["fair_value"] = round(fair, 2)
    out["upside_pct"] = round(100 * upside, 1)
    out["margin_of_safety_pct"] = round(100 * (1 - price / fair), 1) if fair > 0 else None

    if _has(m, "eps_bear", "pe_bear"):
        bear = m["eps_bear"] * m["pe_bear"]
        out["bear_value"] = round(bear, 2)
        out["bear_downside_pct"] = round(100 * (bear / price - 1.0), 1)

    if upside >= UPSIDE_DEEP:
        band = "DEEP_VALUE"
    elif upside >= UPSIDE_BUY:
        band = "VALUE_30"
    elif upside >= 0:
        band = "FAIR"
    else:
        band = "RICH"
    out["value_band"] = band

    # Entry gate — cheap alone is not a buy; demand wash + basing, and a
    # survivable bear case when one is supplied.
    bear_ok = out.get("bear_downside_pct") is None or out["bear_downside_pct"] >= 100 * BEAR_FLOOR
    if band in ("VALUE_30", "DEEP_VALUE"):
        if tech.get("error"):
            out["verdict"] = "GATE-UNKNOWN"     # value case real, chart gate never ran — don't assert a chart fact
        elif tech.get("washed") and tech.get("basing") and bear_ok:
            out["verdict"] = "BUY-CANDIDATE"
        elif tech.get("washed") and not tech.get("basing"):
            out["verdict"] = "WAIT-KNIFE"       # cheap and washed, still falling
        elif not bear_ok:
            out["verdict"] = "WAIT-BEAR-RISK"   # upside real, downside unsurvivable
        else:
            out["verdict"] = "WAIT-NOT-WASHED"  # cheap but never flushed; no forced seller
    else:
        out["verdict"] = "PASS"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metrics", required=True, help="JSON file: list of per-ticker inputs")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for m in json.load(open(args.metrics)):
        try:
            rows.append(evaluate(m))
        except Exception as e:  # one bad candidate must not kill the sweep
            rows.append({"ticker": str(m.get("ticker", "?")).upper(), "legs": {},
                         "verdict": "ERROR", "error": f"{type(e).__name__}: {e}"})
    rows.sort(key=lambda x: x.get("upside_pct") if x.get("upside_pct") is not None else -999,
              reverse=True)
    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(f"{'VERDICT':<16} {'TICKER':<6} {'PRICE':>8} {'FAIR':>8} {'UPSIDE':>8} "
          f"{'BEAR':>7} {'OFF-HI':>7}  LEGS / GATE")
    for x in rows:
        if "upside_pct" not in x:
            print(f"{x.get('verdict','?'):<16} {x['ticker']:<6}  -- insufficient inputs")
            continue
        legs = ",".join(f"{k}={v}" for k, v in x["legs"].items())
        gate = []
        tech = x["tech"]
        if tech.get("error"):
            gate.append("bars n/a")
        else:
            gate.append("washed" if tech["washed"] else "not-washed")
            gate.append(tech["obv_60d"])
            gate.append("SMA50+" if tech["above_sma50"] else "SMA50-")
        ig = (f"  implied g {x['implied_growth_pct']}% vs underwritten "
              f"{x['underwritten_growth_pct']}%" if "implied_growth_pct" in x else "")
        bear = f"{x['bear_downside_pct']:+.0f}%" if x.get("bear_downside_pct") is not None else "--"
        print(f"{x['verdict']:<16} {x['ticker']:<6} {x['price']:>8.2f} {x['fair_value']:>8.2f} "
              f"{x['upside_pct']:>+7.1f}% {bear:>7} {tech.get('off_52wk_high_pct','--'):>6}%  "
              f"{legs} | {'/'.join(gate)}{ig}")
    print("\nRules: BUY-CANDIDATE needs >=30% to the MEDIAN of >=2 independent fair-value legs,"
          "\n       a washed chart (>=20% off high) that is BASING (OBV or SMA50 reclaim),"
          "\n       and a survivable bear case (> -20%) when one is underwritten."
          "\n       Cheap-but-knifing = WAIT. The radar ranks; the desk (and the quality gate,"
          "\n       catalyst scan, and risk committee) still decide.")


if __name__ == "__main__":
    main()
