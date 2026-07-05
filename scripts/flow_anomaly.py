#!/usr/bin/env python3
"""
Unusual money-movement detector for AI Trader — is smart money accumulating or
distributing, and is the stock COILED for a large move up or down?

Pure Python + standard library (no pandas/numpy) so it runs anywhere. It reads
the same historicals JSON as `indicators.py` (and reuses its parsers) and layers
the money-flow / anomaly reads that answer two questions the base indicators
don't, on their own, resolve:

  1. DIRECTION of pressure — who is winning the tape? Buying vs selling pressure
     from where price closes in its range weighted by volume (CMF, A/D line, MFI),
     the sign of the *unusual*-volume days, and effort-vs-result (Wyckoff
     absorption). Plus OBV/A-D **divergence** vs price = accumulation/distribution
     under cover. → `flow_pressure` in [-100, +100].

  2. MAGNITUDE / imminence — is a big move being loaded? Volatility contraction is
     the tell: a Bollinger-in-Keltner squeeze + a low band-width percentile +
     range/ATR contraction = energy coiling for expansion. → `coil_energy` in
     [0, 100].

Combined into a `verdict`: COILED_BULLISH (large-upside setup) / COILED_BEARISH
(large-downside risk) / COILED_UNDIRECTED (energy loaded, wait for the tell) /
EXPANSION_UP / EXPANSION_DOWN (move already underway) / NEUTRAL — with a
confidence (how many independent signals agree) and the trigger levels that would
confirm.

Optional options-flow overlay (`--options <json>`): the desk can't fetch options
from here, so the agent pulls a snapshot via the Robinhood MCP tools
(get_option_quotes / get_option_chains / get_option_historicals) and passes it in.
Any subset of these fields is used if present:
    { "put_call_volume_ratio": 0.6, "put_call_oi_ratio": 0.8,
      "iv_rank": 34, "iv": 0.42, "iv_change_pct": 18,
      "call_volume": 120000, "put_volume": 70000,
      "skew_25d": -3.5,                 # 25d put IV minus call IV; +ve = put-rich (fear)
      "unusual": "large Aug 60c sweep 3x OI" }

Usage:
    python3 flow_anomaly.py <historicals.json>
    python3 flow_anomaly.py <historicals.json> --price 61.20 --float 8.2e8
    python3 flow_anomaly.py <historicals.json> --options opt_snapshot.json
    cat historicals.json | python3 flow_anomaly.py -

Interpretation guide: skills/analysis/money-flow.md. This is a probabilistic read
on a volume-only proxy (can't see dark/off-exchange prints) — confirm with the
chip distribution, the S/R map, and the fundamental thesis. A "coil" in a broken
business that then expands DOWN is not a buy.
"""

import argparse
import json
import os
import sys

# Reuse the battle-tested parsers/indicators from indicators.py (same folder).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import (  # noqa: E402
    _find_bars, _ohlcv, sma, ema_series, atr, bollinger,
)


# --------------------------------------------------------------------------- #
# Money-flow primitives (buying vs selling pressure)
# --------------------------------------------------------------------------- #

def _money_flow_multiplier(h, l, c):
    """Where the bar closed in its range, [-1, +1]. +1 = closed at high (demand
    absorbed the bar), -1 = closed at low (supply won). Flat bar → 0."""
    rng = h - l
    if rng <= 0:
        return 0.0
    return ((c - l) - (h - c)) / rng


def ad_line(highs, lows, closes, volumes):
    """Accumulation/Distribution line (Williams) — cumulative volume weighted by
    where each bar closes in its range. Rising = accumulation, falling = distribution."""
    if not volumes or sum(volumes) == 0:
        return None
    ad, series = 0.0, []
    for i in range(len(closes)):
        ad += _money_flow_multiplier(highs[i], lows[i], closes[i]) * volumes[i]
        series.append(ad)
    return series


def ad_slope(highs, lows, closes, volumes, period=20):
    """Normalized A/D slope over `period`, bounded [-1, +1]: net signed volume as a
    fraction of gross volume traded in the window (since MFM ∈ [-1, 1])."""
    series = ad_line(highs, lows, closes, volumes)
    if not series or len(series) < period + 1:
        return None
    gross = sum(volumes[-period:])
    if gross <= 0:
        return None
    return max(-1.0, min(1.0, (series[-1] - series[-period - 1]) / gross))


def cmf(highs, lows, closes, volumes, period=20):
    """Chaikin Money Flow — sum(MFM*vol)/sum(vol) over `period`, in [-1, +1].
    > +0.05 buying pressure, < -0.05 selling pressure, near 0 balanced."""
    if not volumes or len(closes) < period or sum(volumes[-period:]) == 0:
        return None
    mfv = sum(_money_flow_multiplier(highs[i], lows[i], closes[i]) * volumes[i]
              for i in range(len(closes) - period, len(closes)))
    vol = sum(volumes[-period:])
    return mfv / vol if vol else None


def mfi(highs, lows, closes, volumes, period=14):
    """Money Flow Index — a volume-weighted RSI on typical price, [0, 100].
    > 80 overbought / < 20 oversold; divergences flag exhaustion."""
    if not volumes or len(closes) < period + 1 or sum(volumes) == 0:
        return None
    tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
    pos, neg = 0.0, 0.0
    for i in range(len(closes) - period, len(closes)):
        rmf = tp[i] * volumes[i]
        if tp[i] > tp[i - 1]:
            pos += rmf
        elif tp[i] < tp[i - 1]:
            neg += rmf
    if neg == 0:
        return 100.0 if pos > 0 else 50.0
    ratio = pos / neg
    return 100 - (100 / (1 + ratio))


# --------------------------------------------------------------------------- #
# Unusual volume + effort-vs-result
# --------------------------------------------------------------------------- #

def _mean_std(xs):
    n = len(xs)
    if n == 0:
        return None, None
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    return m, var ** 0.5


def volume_zscore(volumes, lookback=50):
    """How statistically unusual today's volume is vs its recent distribution.
    z>2 ≈ a genuine surge (top ~2.5%); z>3 is rare. More honest than a fixed
    1.5x threshold because it accounts for how noisy the name's volume is."""
    if not volumes or len(volumes) < lookback + 1 or sum(volumes[-lookback - 1:-1]) == 0:
        return None
    hist = volumes[-lookback - 1:-1]
    m, sd = _mean_std(hist)
    if not sd:
        return None
    return (volumes[-1] - m) / sd


def signed_surge(highs, lows, closes, volumes, lookback=10):
    """Among the last `lookback` bars, find the most unusual-volume bar and report
    its DIRECTION. A surge on an up-close bar = demand showing its hand; on a
    down-close bar = supply. Returns (signed_score[-1..1], detail)."""
    if not volumes or len(volumes) < lookback + 2 or sum(volumes) == 0:
        return None
    m, sd = _mean_std(volumes[-lookback - 50:-lookback] or volumes[:-lookback] or volumes)
    if not sd:
        return None
    best_i, best_z = None, 0.0
    for i in range(len(closes) - lookback, len(closes)):
        z = (volumes[i] - m) / sd
        if abs(z) > abs(best_z):
            # direction = where the bar closed in its range (demand vs supply)
            best_z, best_i = z, i
    if best_i is None or best_z <= 0:
        return None
    mfm = _money_flow_multiplier(highs[best_i], lows[best_i], closes[best_i])
    # scale surge magnitude (z, capped ~3) by close-location bias
    score = max(-1.0, min(1.0, mfm * min(best_z / 3.0, 1.0)))
    bars_ago = len(closes) - 1 - best_i
    detail = (f"{'up' if mfm > 0 else 'down'}-bar volume surge z={best_z:.1f} "
              f"{bars_ago}d ago, closed {int(round((mfm + 1) / 2 * 100))}% up its range")
    return score, detail


def effort_vs_result(highs, lows, closes, volumes, atr_val):
    """Wyckoff effort (volume) vs result (price progress). High effort + little
    result = absorption: someone big is soaking supply/demand without moving price.
    At a low that's accumulation (bullish); at a high, distribution (bearish)."""
    if not volumes or len(closes) < 3 or not atr_val:
        return None
    vz = volume_zscore(volumes)
    if vz is None:
        return None
    move_atr = abs(closes[-1] - closes[-2]) / atr_val if atr_val else None
    if move_atr is None:
        return None
    if vz >= 1.5 and move_atr < 0.4:
        mfm = _money_flow_multiplier(highs[-1], lows[-1], closes[-1])
        bias = "bullish (demand absorbing supply)" if mfm >= 0 else "bearish (supply capping demand)"
        return {"state": "absorption", "vol_z": round(vz, 2),
                "move_atr": round(move_atr, 2), "bias": bias,
                "note": f"heavy volume (z={vz:.1f}) but price barely moved ({move_atr:.2f} ATR) — {bias}"}
    if vz >= 1.5 and move_atr >= 1.2:
        return {"state": "expansion", "vol_z": round(vz, 2), "move_atr": round(move_atr, 2),
                "bias": "trend confirmed by volume",
                "note": f"volume (z={vz:.1f}) and range ({move_atr:.2f} ATR) both expanding — move underway"}
    if vz < -0.5 and move_atr < 0.5:
        return {"state": "quiet", "vol_z": round(vz, 2), "move_atr": round(move_atr, 2),
                "bias": "no demand/supply commitment", "note": "volume drying up in a tight range — coiling"}
    return {"state": "normal", "vol_z": round(vz, 2), "move_atr": round(move_atr, 2)}


# --------------------------------------------------------------------------- #
# Divergence (accumulation / distribution under cover)
# --------------------------------------------------------------------------- #

def _pct_change(seq, period):
    if len(seq) < period + 1 or seq[-period - 1] == 0:
        return None
    return (seq[-1] - seq[-period - 1]) / abs(seq[-period - 1])


def divergence(closes, volumes, highs, lows, period=20):
    """Compare the price trend to the A/D and OBV trends over `period`.
    Price DOWN while flow UP  = bullish divergence (accumulation under cover).
    Price UP while flow DOWN  = bearish divergence (distribution under cover)."""
    if not volumes or len(closes) < period + 1 or sum(volumes) == 0:
        return None
    price_chg = _pct_change(closes, period)
    ad = ad_line(highs, lows, closes, volumes)
    ad_chg = (ad[-1] - ad[-period - 1]) / (sum(volumes[-period:]) or 1) if ad else None
    # OBV
    obv_s = [0.0]
    for i in range(1, len(closes)):
        obv_s.append(obv_s[-1] + (volumes[i] if closes[i] > closes[i - 1]
                                  else -volumes[i] if closes[i] < closes[i - 1] else 0.0))
    obv_chg = (obv_s[-1] - obv_s[-period - 1]) / (sum(volumes[-period:]) or 1)
    if price_chg is None:
        return None
    flow = ((ad_chg or 0) + obv_chg) / 2  # both already normalized to gross volume
    kind, note = None, None
    if price_chg < -0.02 and flow > 0.05:
        kind = "bullish"
        note = f"price {price_chg*100:+.0f}% but volume-flow rising — accumulation under cover"
    elif price_chg > 0.02 and flow < -0.05:
        kind = "bearish"
        note = f"price {price_chg*100:+.0f}% but volume-flow falling — distribution under cover"
    return {"kind": kind, "price_chg_pct": round(price_chg * 100, 1),
            "flow_norm": round(flow, 3), "note": note}


# --------------------------------------------------------------------------- #
# Squeeze / coil — the magnitude-of-impending-move engine
# --------------------------------------------------------------------------- #

def _bbw_series(closes, period=20, mult=2.0):
    """Bollinger band-width (as % of mid) for every bar we can compute it on."""
    out = []
    for i in range(period, len(closes) + 1):
        w = closes[i - period:i]
        mid = sum(w) / period
        sd = (sum((x - mid) ** 2 for x in w) / period) ** 0.5
        out.append((2 * mult * sd) / mid * 100 if mid else 0.0)
    return out


def _keltner(highs, lows, closes, period=20, mult=1.5):
    """Keltner channel width (%) at the last bar: EMA ± mult*ATR."""
    mid_s = ema_series(closes, period)
    a = atr(highs, lows, closes, period)
    if not mid_s or a is None or mid_s[-1] == 0:
        return None
    return (mid_s[-1], 2 * mult * a / mid_s[-1] * 100, a)


def squeeze_coil(highs, lows, closes, volumes, atr_val):
    """Is the stock coiling (volatility contracting) — loading energy for a large
    move? Combines: TTM-style squeeze (Bollinger inside Keltner), band-width
    percentile (how tight vs its own recent history), ATR contraction, and volume
    dry-up. Returns coil_energy in [0, 100] plus the components."""
    if len(closes) < 40:
        return None
    bb = bollinger(closes, 20, 2)
    kc = _keltner(highs, lows, closes, 20, 1.5)
    bbw_series = _bbw_series(closes, 20, 2.0)
    if not bb or not kc or len(bbw_series) < 10:
        return None
    cur_bbw = bbw_series[-1]
    hist = bbw_series[-126:] if len(bbw_series) >= 30 else bbw_series
    pctile = sum(1 for x in hist if x <= cur_bbw) / len(hist)  # 0 = tightest it's been

    squeeze_on = (kc is not None and bb["upper"] - bb["lower"] < kc[1] / 100 * kc[0])

    energy = 0.0
    comps = {}
    if squeeze_on:
        energy += 45
    comps["squeeze_on"] = squeeze_on
    energy += (1 - pctile) * 35
    comps["bandwidth_pctile"] = round(pctile, 2)

    # ATR contraction vs ~1 month ago
    atr_prior = atr(highs[:-20], lows[:-20], closes[:-20], 14) if len(closes) > 55 else None
    if atr_prior and atr_val and atr_val < atr_prior:
        contraction = min((atr_prior - atr_val) / atr_prior, 0.5) / 0.5  # 0..1
        energy += contraction * 12
        comps["atr_contraction"] = round((atr_prior - atr_val) / atr_prior, 2)

    # volume dry-up in the base (quiet accumulation/complacency before expansion)
    if volumes and len(volumes) >= 25 and sum(volumes[-20:]) > 0:
        recent = sum(volumes[-5:]) / 5
        base = sum(volumes[-25:-5]) / 20
        if base and recent < base:
            energy += min((base - recent) / base, 0.5) / 0.5 * 8
            comps["volume_dryup"] = round(recent / base, 2)

    energy = max(0.0, min(100.0, energy))
    label = ("tightly coiled" if energy >= 70 else "coiling" if energy >= 50
             else "some contraction" if energy >= 30 else "not coiled")
    comps["cur_bandwidth_pct"] = round(cur_bbw, 2)
    return {"coil_energy": round(energy, 0), "label": label, **comps}


# --------------------------------------------------------------------------- #
# Options-flow overlay (agent-sourced snapshot)
# --------------------------------------------------------------------------- #

def options_read(opt):
    """Turn an options snapshot into a signed directional lean [-1..+1] + notes.
    Tolerant of missing fields — uses whatever the agent supplied."""
    if not isinstance(opt, dict) or not opt:
        return None
    score, weight, notes = 0.0, 0.0, []

    pcv = opt.get("put_call_volume_ratio")
    if pcv is not None:
        # low P/C (<0.7) = call-heavy/bullish speculation; high (>1.2) = put-heavy/hedging
        s = max(-1.0, min(1.0, (0.9 - pcv) / 0.5))
        score += s * 0.35; weight += 0.35
        notes.append(f"put/call volume {pcv} ({'call-heavy' if pcv < 0.8 else 'put-heavy' if pcv > 1.1 else 'balanced'})")

    pco = opt.get("put_call_oi_ratio")
    if pco is not None:
        s = max(-1.0, min(1.0, (0.9 - pco) / 0.6))
        score += s * 0.15; weight += 0.15
        notes.append(f"put/call OI {pco}")

    skew = opt.get("skew_25d")
    if skew is not None:
        # positive skew (put IV > call IV) = downside fear priced; negative = call demand
        s = max(-1.0, min(1.0, -skew / 5.0))
        score += s * 0.25; weight += 0.25
        notes.append(f"25d skew {skew:+.1f} ({'put-rich/fear' if skew > 1 else 'call-rich/greed' if skew < -1 else 'flat'})")

    ivr = opt.get("iv_rank")
    ivc = opt.get("iv_change_pct")
    if ivr is not None:
        notes.append(f"IV rank {ivr} ({'rich' if ivr > 60 else 'cheap' if ivr < 25 else 'mid'})")
    if ivc is not None:
        notes.append(f"IV {ivc:+.0f}% ({'expanding — event/positioning' if ivc > 10 else 'stable'})")

    if opt.get("unusual"):
        notes.append(f"unusual: {opt['unusual']}")

    lean = (score / weight) if weight else None
    return {"lean": round(lean, 2) if lean is not None else None,
            "iv_rank": ivr, "iv_change_pct": ivc, "notes": "; ".join(notes)}


# --------------------------------------------------------------------------- #
# Assembly — pressure, coil, verdict
# --------------------------------------------------------------------------- #

def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def build(bars, price_override=None, float_shares=None, options=None):
    o, h, l, c, v = _ohlcv(bars)
    if len(c) < 20:
        return {"error": f"need >=20 bars, got {len(c)}"}
    has_hl = any(h[i] != c[i] or l[i] != c[i] for i in range(len(c)))
    has_vol = bool(v) and sum(v) > 0
    price = price_override if price_override is not None else c[-1]
    atr14 = atr(h, l, c, 14)

    cmf20 = cmf(h, l, c, v)
    mfi14 = mfi(h, l, c, v)
    ads = ad_slope(h, l, c, v)
    vz = volume_zscore(v)
    surge = signed_surge(h, l, c, v)
    evr = effort_vs_result(h, l, c, v, atr14)
    div = divergence(c, v, h, l)
    coil = squeeze_coil(h, l, c, v, atr14)
    opt = options_read(options)

    # -- Directional flow pressure: weighted blend of the independent reads -----
    parts, wsum, contrib = 0.0, 0.0, {}
    def add(name, val, weight):
        nonlocal parts, wsum
        if val is not None:
            parts += _clamp(val) * weight
            wsum += weight
            contrib[name] = round(_clamp(val), 2)
    add("cmf", (cmf20 / 0.2) if cmf20 is not None else None, 0.28)
    add("mfi", ((mfi14 - 50) / 50) if mfi14 is not None else None, 0.17)
    add("ad_slope", ads, 0.25)
    add("signed_surge", surge[0] if surge else None, 0.18)
    if opt and opt.get("lean") is not None:
        add("options", opt["lean"], 0.22)
    flow_pressure = round((parts / wsum) * 100, 0) if wsum else None

    # -- Confidence: how many independent signals agree on direction -----------
    votes = []
    for nm in ("cmf", "mfi", "ad_slope", "signed_surge", "options"):
        if nm in contrib and abs(contrib[nm]) >= 0.1:
            votes.append(1 if contrib[nm] > 0 else -1)
    if div and div.get("kind"):
        votes.append(1 if div["kind"] == "bullish" else -1)
    agree = 0
    if votes and flow_pressure is not None:
        side = 1 if flow_pressure >= 0 else -1
        agree = sum(1 for x in votes if x == side)
    conf = ("high" if len(votes) >= 4 and agree >= len(votes) - 1
            else "medium" if len(votes) >= 2 and agree >= max(2, len(votes) - 1)
            else "low")

    coil_energy = coil["coil_energy"] if coil else None
    rel_now = (v[-1] / (sum(v[-21:-1]) / 20)) if (has_vol and len(v) >= 21 and sum(v[-21:-1])) else None

    # -- Trigger levels (breakout/breakdown that confirms the move) ------------
    look = min(20, len(c) - 1)
    hi_trig = round(max(h[-look:]), 2)
    lo_trig = round(min(l[-look:]), 2)

    # -- Verdict ---------------------------------------------------------------
    fp = flow_pressure or 0
    strong = abs(fp) >= 25
    coiled = coil_energy is not None and coil_energy >= 55
    expanding_now = (rel_now is not None and rel_now >= 1.8) or (evr and evr.get("state") == "expansion")

    if expanding_now and strong:
        verdict = "EXPANSION_UP" if fp > 0 else "EXPANSION_DOWN"
        headline = ("Move underway — volume expanding with buying pressure; chase only on a "
                    "confirmed hold above trigger." if fp > 0 else
                    "Breakdown underway — volume expanding with selling pressure; protect/avoid.")
    elif coiled and strong:
        verdict = "COILED_BULLISH" if fp > 0 else "COILED_BEARISH"
        headline = (f"Coiled ({coil['label']}) with net {'buying' if fp > 0 else 'selling'} "
                    f"pressure — set up for a large {'UP' if fp > 0 else 'DOWN'} move; "
                    f"trigger { hi_trig if fp > 0 else lo_trig }.")
    elif coiled:
        verdict = "COILED_UNDIRECTED"
        headline = (f"Energy loaded ({coil['label']}) but direction unconfirmed — wait for the "
                    f"break: long above {hi_trig}, short below {lo_trig}, with volume.")
    elif strong:
        verdict = "PRESSURE_BUILDING_UP" if fp > 0 else "PRESSURE_BUILDING_DOWN"
        headline = (f"Net {'accumulation' if fp > 0 else 'distribution'} pressure without a coil "
                    f"yet — {'watch for a base to tighten' if fp > 0 else 'rallies likely sold'}.")
    else:
        verdict = "NEUTRAL"
        headline = "No unusual money movement — balanced tape, no imminent large-move setup."

    result = {
        "n_bars": len(c), "has_high_low": has_hl, "has_volume": has_vol,
        "price": round(price, 4),
        "verdict": verdict, "headline": headline,
        "flow_pressure": flow_pressure,      # -100 (heavy distribution) .. +100 (heavy accumulation)
        "coil_energy": coil_energy,          # 0 (loose) .. 100 (tightly coiled)
        "confidence": conf,
        "signals_agree": f"{agree}/{len(votes)}" if votes else None,
        "pressure_components": contrib,
        "money_flow": {
            "cmf_20": round(cmf20, 3) if cmf20 is not None else None,
            "mfi_14": round(mfi14, 1) if mfi14 is not None else None,
            "ad_slope_20": round(ads, 3) if ads is not None else None,
            "volume_zscore": round(vz, 2) if vz is not None else None,
            "rel_volume_now": round(rel_now, 2) if rel_now is not None else None,
        },
        "unusual_volume": {"signed_surge": round(surge[0], 2), "detail": surge[1]} if surge else None,
        "effort_vs_result": evr,
        "divergence": div if (div and div.get("kind")) else None,
        "squeeze_coil": coil,
        "options_flow": opt,
        "triggers": {"breakout_above": hi_trig, "breakdown_below": lo_trig,
                     "note": "confirm a large move with a close beyond the trigger on rel-volume > ~1.8x"},
    }

    # -- Plain-English summary -------------------------------------------------
    notes = [headline]
    if flow_pressure is not None:
        notes.append(f"flow pressure {flow_pressure:+.0f}/100 ({conf} confidence, {result['signals_agree']} agree)")
    if coil_energy is not None:
        notes.append(f"coil energy {coil_energy:.0f}/100 ({coil['label']})")
    if div and div.get("kind"):
        notes.append(div["note"])
    if evr and evr.get("note") and evr["state"] in ("absorption", "expansion", "quiet"):
        notes.append(evr["note"])
    if surge:
        notes.append(surge[1])
    if opt and opt.get("notes"):
        notes.append("options — " + opt["notes"])
    if not has_vol:
        notes.append("WARNING: no volume in feed — money-flow reads unavailable/degraded")
    elif not has_hl:
        notes.append("WARNING: no high/low in feed — range-based reads degraded to closes")
    result["summary"] = "; ".join(notes)
    return result


def main():
    p = argparse.ArgumentParser(
        description="Unusual money-movement detector: flow pressure + coil energy → large-move verdict.")
    p.add_argument("source", help="historicals JSON file, or '-' for stdin")
    p.add_argument("--price", type=float, default=None, help="override current price (live quote)")
    p.add_argument("--float", type=float, default=None, dest="float_shares",
                   help="circulating float (shares) — reserved for parity with indicators.py")
    p.add_argument("--options", default=None,
                   help="options snapshot JSON file (agent-sourced from Robinhood MCP) for the flow overlay")
    args = p.parse_args()

    raw = sys.stdin.read() if args.source == "-" else open(args.source).read()
    bars = _find_bars(json.loads(raw))
    if not bars:
        print(json.dumps({"error": "could not locate price bars in input"}))
        sys.exit(1)
    options = None
    if args.options:
        try:
            options = json.loads(open(args.options).read())
        except (OSError, ValueError) as e:
            print(json.dumps({"error": f"could not read --options: {e}"}))
            sys.exit(1)
    out = build(bars, price_override=args.price, float_shares=args.float_shares, options=options)
    if "error" in out:
        print(json.dumps(out))
        sys.exit(1)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
