#!/usr/bin/env python3
"""
Chart renderer for AI Trader — turns the numbers from
``indicators.py`` into self-contained **SVG** the daily report can embed.

Why SVG (and why pure stdlib): the reports are markdown committed to GitHub and
also read in local previewers. SVG is vector-crisp, tiny, renders inline on
GitHub via a relative image link, and — crucially — can be generated with plain
string templating, so this stays a **no-install** module like ``indicators.py``
(no matplotlib/numpy). Everything is one self-contained file per chart with an
explicit dark background, so it reads the same in GitHub's light or dark theme.

It produces three views per name:
  1. price+volume  — candlesticks, SMA 20/50/200, Bollinger band, the
                     support/resistance ladder as shaded zones, and the current
                     price line (the "where does it trade against structure" view).
  2. chips         — the chip / cost-basis distribution as a horizontal
                     histogram: profit vs. trapped split, main cost-basis shelf,
                     high-volume nodes (the institutional-footprint view).
  3. gauges        — a compact signal dashboard: RSI, Stochastic, ADX, relative
                     volume as meters, plus trend/MACD/OBV badges (the "read it
                     at a glance" view).

Plus ``sparkline()`` — a unicode price sparkline for inline use in the watchlist
scan lines (no file needed).

Usage:
    python3 scripts/charts.py <historicals.json> --symbol SOFI --price 18.26 \
        --float 1.259e9 --out reports/charts
    cat historicals.json | python3 scripts/charts.py - --symbol SOFI --out reports/charts

It reuses ``indicators.py`` for bar parsing, the indicator suite, and the chip
bins, so the chart and the numbers can never disagree. It prints the written
file paths and a ready-to-paste markdown embed block (last lines).
"""

import argparse
import json
import os
import sys

import indicators as ind


# --------------------------------------------------------------------------- #
# Palette — a dark "terminal" theme that reads on both GitHub light & dark.
# --------------------------------------------------------------------------- #

BG      = "#0d1117"   # GitHub dark canvas
PANEL   = "#11161d"
GRID    = "#222b36"
AXIS    = "#30363d"
TEXT    = "#c9d1d9"
MUTED   = "#8b949e"
UP      = "#26a69a"   # green candle / accumulation
DOWN    = "#ef5350"   # red candle / distribution
SMA20   = "#f0b90b"   # amber
SMA50   = "#58a6ff"   # blue
SMA200  = "#bc8cff"   # purple
BOLL    = "#8b949e"   # bollinger band edge
PRICE   = "#e6edf3"   # current-price line
SUPPORT = "#26a69a"
RESIST  = "#ef5350"
COST    = "#f0b90b"   # main cost basis
FONT    = "font-family='ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif'"
MONO    = "font-family='ui-monospace,SFMono-Regular,Menlo,monospace'"


# --------------------------------------------------------------------------- #
# Tiny SVG helpers
# --------------------------------------------------------------------------- #

def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _n(x):
    """Format a coordinate compactly (SVG doesn't need long decimals)."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _line(x1, y1, x2, y2, stroke, w=1, dash=None, opacity=None):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    o = f" stroke-opacity='{opacity}'" if opacity is not None else ""
    return (f"<line x1='{_n(x1)}' y1='{_n(y1)}' x2='{_n(x2)}' y2='{_n(y2)}' "
            f"stroke='{stroke}' stroke-width='{w}'{d}{o}/>")


def _rect(x, y, w, h, fill, opacity=None, rx=None, stroke=None, sw=None):
    o = f" fill-opacity='{opacity}'" if opacity is not None else ""
    r = f" rx='{rx}'" if rx else ""
    s = f" stroke='{stroke}' stroke-width='{sw or 1}'" if stroke else ""
    return (f"<rect x='{_n(x)}' y='{_n(y)}' width='{_n(w)}' height='{_n(h)}' "
            f"fill='{fill}'{o}{r}{s}/>")


def _text(x, y, s, fill=TEXT, size=11, anchor="start", weight=None, mono=False):
    f = MONO if mono else FONT
    w = f" font-weight='{weight}'" if weight else ""
    return (f"<text x='{_n(x)}' y='{_n(y)}' {f} font-size='{size}' fill='{fill}' "
            f"text-anchor='{anchor}'{w}>{_esc(s)}</text>")


def _polyline(points, stroke, w=1.5, opacity=None):
    if not points:
        return ""
    pts = " ".join(f"{_n(x)},{_n(y)}" for x, y in points)
    o = f" stroke-opacity='{opacity}'" if opacity is not None else ""
    return (f"<polyline points='{pts}' fill='none' stroke='{stroke}' "
            f"stroke-width='{w}' stroke-linejoin='round'{o}/>")


def _svg(w, h, body, title=""):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' "
            f"width='{w}' height='{h}' role='img'>"
            f"<title>{_esc(title)}</title>"
            f"{_rect(0, 0, w, h, BG, rx=8)}{body}</svg>")


def _scaler(d0, d1, r0, r1):
    """Linear map data→pixels. Degenerate domain collapses to the range midpoint."""
    if d1 == d0:
        return lambda _v: (r0 + r1) / 2
    m = (r1 - r0) / (d1 - d0)
    return lambda v: r0 + (v - d0) * m


def _rolling_mean(xs, p):
    """Rolling SMA series aligned to xs (None until enough history)."""
    out = [None] * len(xs)
    s = 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= p:
            s -= xs[i - p]
        if i >= p - 1:
            out[i] = s / p
    return out


def _rolling_std(xs, p):
    out = [None] * len(xs)
    for i in range(p - 1, len(xs)):
        w = xs[i - p + 1:i + 1]
        m = sum(w) / p
        out[i] = (sum((v - m) ** 2 for v in w) / p) ** 0.5
    return out


def _nice_ticks(lo, hi, n=5):
    """A handful of round-ish price gridlines between lo and hi."""
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / n
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 0.1 ** (
        1 + len(str(int(1 / raw))) if raw > 0 else 1)
    for step in (mag, mag * 2, mag * 2.5, mag * 5, mag * 10):
        if (hi - lo) / step <= n + 1:
            break
    import math
    start = math.ceil(lo / step) * step
    ticks, v = [], start
    while v <= hi + 1e-9:
        ticks.append(round(v, 4))
        v += step
    return ticks or [lo, hi]


# --------------------------------------------------------------------------- #
# 1) Price + volume + support/resistance
# --------------------------------------------------------------------------- #

def render_price_volume(symbol, o, h, l, c, v, dates, indi, price, lookback=180):
    """Candlestick price chart with MAs, Bollinger band, S/R zones and volume."""
    # Compute the moving-average / Bollinger series on the FULL history first, then
    # trim to the most recent `lookback` bars for display — otherwise a 200-period
    # SMA would never have enough points inside a 180-bar window.
    mid_f = _rolling_mean(c, 20)
    sd_f = _rolling_std(c, 20)
    ma_f = {p: _rolling_mean(c, p) for p in (20, 50, 200)}
    avg_f = _rolling_mean(v, 20)

    n_all = len(c)
    start = max(0, n_all - lookback)
    o, h, l, c, v = o[start:], h[start:], l[start:], c[start:], v[start:]
    dates = dates[start:]
    mid, sd = mid_f[start:], sd_f[start:]
    ma = {p: ma_f[p][start:] for p in ma_f}
    avg20 = avg_f[start:]
    n = len(c)

    W, H = 940, 520
    ml, mr, mt, mb = 8, 66, 44, 26
    vol_h = 90                      # volume sub-panel height
    gap = 10
    price_top = mt
    price_bot = H - mb - vol_h - gap
    vol_top = price_bot + gap
    vol_bot = H - mb

    lo = min(l); hi = max(h)
    pad = (hi - lo) * 0.06 or hi * 0.02
    lo -= pad; hi += pad
    x = _scaler(0, max(n - 1, 1), ml, W - mr)
    y = _scaler(lo, hi, price_bot, price_top)
    step = (W - mr - ml) / max(n, 1)
    body_w = max(1.2, step * 0.62)

    parts = []
    parts.append(_rect(ml, price_top, W - mr - ml, price_bot - price_top, PANEL, rx=6))

    # price gridlines + right-axis labels
    for t in _nice_ticks(lo + pad, hi - pad, 5):
        yy = y(t)
        parts.append(_line(ml, yy, W - mr, yy, GRID, 1))
        parts.append(_text(W - mr + 5, yy + 3, _n(t), MUTED, 10, mono=True))

    # Bollinger band (20,2) as a faint envelope for volatility context
    up_pts, dn_pts = [], []
    for i in range(n):
        if mid[i] is not None and sd[i] is not None:
            up_pts.append((x(i), y(mid[i] + 2 * sd[i])))
            dn_pts.append((x(i), y(mid[i] - 2 * sd[i])))
    if up_pts:
        poly = " ".join(f"{_n(px)},{_n(py)}" for px, py in up_pts + dn_pts[::-1])
        parts.append(f"<polygon points='{poly}' fill='{BOLL}' fill-opacity='0.06'/>")
        parts.append(_polyline(up_pts, BOLL, 0.8, opacity=0.35))
        parts.append(_polyline(dn_pts, BOLL, 0.8, opacity=0.35))

    # support / resistance zones from the indicator ladders
    sr = indi.get("support_resistance") or {}
    for z in (sr.get("support_ladder") or [])[:3]:
        yy = y(z["level"])
        if price_top <= yy <= price_bot:
            parts.append(_line(ml, yy, W - mr, yy, SUPPORT, 1, dash="5 4", opacity=0.7))
            parts.append(_text(ml + 6, yy - 3, f"S {_n(z['level'])} · {z['touches']}x",
                               SUPPORT, 9.5, mono=True))
    for z in (sr.get("resistance_ladder") or [])[:3]:
        yy = y(z["level"])
        if price_top <= yy <= price_bot:
            parts.append(_line(ml, yy, W - mr, yy, RESIST, 1, dash="5 4", opacity=0.7))
            parts.append(_text(ml + 6, yy + 11, f"R {_n(z['level'])} · {z['touches']}x",
                               RESIST, 9.5, mono=True))

    # candles
    for i in range(n):
        cx = x(i)
        col = UP if c[i] >= o[i] else DOWN
        parts.append(_line(cx, y(h[i]), cx, y(l[i]), col, 1))
        y_o, y_c = y(o[i]), y(c[i])
        top = min(y_o, y_c)
        bh = max(abs(y_c - y_o), 1)
        parts.append(_rect(cx - body_w / 2, top, body_w, bh, col))

    # moving averages
    for period, colr in ((20, SMA20), (50, SMA50), (200, SMA200)):
        ser = ma[period]
        pts = [(x(i), y(ser[i])) for i in range(n) if ser[i] is not None]
        if len(pts) > 1:
            parts.append(_polyline(pts, colr, 1.6))

    # current price line + right-edge pill
    yp = y(price)
    parts.append(_line(ml, yp, W - mr, yp, PRICE, 1, dash="2 3"))
    parts.append(_rect(W - mr, yp - 8, mr - 2, 16, PRICE, rx=3))
    parts.append(_text(W - mr + (mr - 2) / 2, yp + 3.5, _n(price), BG, 10, "middle",
                       weight="700", mono=True))

    # volume sub-panel
    parts.append(_rect(ml, vol_top, W - mr - ml, vol_bot - vol_top, PANEL, rx=6))
    vmax = max(v) or 1
    vy = _scaler(0, vmax, vol_bot, vol_top)
    for i in range(n):
        col = UP if c[i] >= o[i] else DOWN
        vh = vol_bot - vy(v[i])
        parts.append(_rect(x(i) - body_w / 2, vy(v[i]), body_w, vh, col, opacity=0.55))
    avg_pts = [(x(i), vy(avg20[i])) for i in range(n) if avg20[i] is not None]
    if len(avg_pts) > 1:
        parts.append(_polyline(avg_pts, MUTED, 1, opacity=0.8))
    parts.append(_text(ml + 6, vol_top + 13, "Volume (20-day avg —)", MUTED, 9.5))

    # x-axis date labels (~6 across)
    idxs = sorted(set([0, n - 1] + [round(k * (n - 1) / 5) for k in range(1, 5)]))
    for i in idxs:
        d = dates[i][:10] if i < len(dates) and dates[i] else ""
        if d:
            parts.append(_text(x(i), H - mb + 16, d[5:], MUTED, 9, "middle", mono=True))

    # header
    parts.append(_text(ml + 4, 20, f"{symbol}", TEXT, 16, weight="700"))
    parts.append(_text(ml + 4, 35, f"{price:.2f}", TEXT, 12, mono=True))
    parts.append(_text(ml + 70, 20, "SMA20", SMA20, 10))
    parts.append(_text(ml + 116, 20, "SMA50", SMA50, 10))
    parts.append(_text(ml + 162, 20, "SMA200", SMA200, 10))
    rng = indi.get("range_52w") or {}
    if rng:
        parts.append(_text(W - mr, 20, f"52w {_n(rng.get('low'))}–{_n(rng.get('high'))}",
                           MUTED, 10, "end", mono=True))
    return _svg(W, H, "".join(parts), f"{symbol} price / volume")


# --------------------------------------------------------------------------- #
# 2) Chip / cost-basis distribution
# --------------------------------------------------------------------------- #

def render_chips(symbol, centers, chips, width, price, chip_summary):
    """Horizontal chip-distribution histogram: price on the y-axis, share of chips
    extending right; green below the price (in profit), red above (trapped)."""
    W, H = 480, 520
    ml, mr, mt, mb = 60, 150, 44, 26
    total = sum(chips)
    frac = [ck / total for ck in chips]
    lo = centers[0] - width / 2
    hi = centers[-1] + width / 2
    y = _scaler(hi, lo, mt, H - mb)                 # high price at top
    fmax = max(frac) or 1
    x = _scaler(0, fmax, ml, W - mr)
    bar_h = max(1.5, (H - mb - mt) / len(frac) - 1)

    parts = [_rect(ml, mt, W - mr - ml, H - mb - mt, PANEL, rx=6)]

    # price gridlines
    for t in _nice_ticks(lo, hi, 6):
        yy = y(t)
        if mt <= yy <= H - mb:
            parts.append(_line(ml, yy, W - mr, yy, GRID, 1))
            parts.append(_text(ml - 6, yy + 3, _n(t), MUTED, 10, "end", mono=True))

    # bars, colored by profit/trapped relative to current price
    for i, ck in enumerate(frac):
        yy = y(centers[i])
        col = SUPPORT if centers[i] < price else RESIST
        parts.append(_rect(ml, yy - bar_h / 2, x(ck) - ml, bar_h, col, opacity=0.85))

    # current price line
    yp = y(price)
    parts.append(_line(ml, yp, W - mr, yp, PRICE, 1.2, dash="3 3"))
    parts.append(_rect(W - mr, yp - 8, mr - 4, 16, PRICE, rx=3))
    parts.append(_text(W - mr + (mr - 4) / 2, yp + 3.5, f"{price:.2f}", BG, 10, "middle",
                       weight="700", mono=True))

    # main cost basis + HVN labels on the right rail
    cs = chip_summary or {}
    rail = W - mr + 4
    ry = mt + 14
    parts.append(_text(rail, ry, "cost basis", TEXT, 10, weight="700"))
    ry += 16
    mcb = cs.get("main_cost_basis") or {}
    if mcb:
        parts.append(_line(ml, y(mcb["price"]), W - mr, y(mcb["price"]), COST, 1.4))
        parts.append(_text(rail, ry, f"main ~{_n(mcb['price'])} ({mcb['pct_chips']}%)",
                           COST, 9.5, mono=True))
        ry += 14
    for z in (cs.get("high_volume_nodes") or [])[:4]:
        col = SUPPORT if z["side"] == "support" else RESIST
        parts.append(_text(rail, ry, f"{z['side'][:3]} {_n(z['price'])} ({z['pct_chips']}%)",
                           col, 9.5, mono=True))
        ry += 13
    ry += 6
    prof = cs.get("pct_in_profit")
    trap = cs.get("pct_trapped_overhead")
    if prof is not None:
        parts.append(_text(rail, ry, f"profit {prof:.0f}%", SUPPORT, 9.5, mono=True)); ry += 13
        parts.append(_text(rail, ry, f"trapped {trap:.0f}%", RESIST, 9.5, mono=True)); ry += 13
    conc = cs.get("concentration")
    if conc:
        parts.append(_text(rail, ry, f"{conc}", MUTED, 9.5)); ry += 13
        parts.append(_text(rail, ry, f"({cs.get('concentration_pct')}% of px)", MUTED, 9)); ry += 13

    # profit / trapped split legend (bottom)
    parts.append(_text(ml, 20, f"{symbol} — chip distribution", TEXT, 14, weight="700"))
    parts.append(_rect(ml, mt - 14, 9, 9, SUPPORT)); parts.append(_text(ml + 13, mt - 6, "in profit", MUTED, 9))
    parts.append(_rect(ml + 78, mt - 14, 9, 9, RESIST)); parts.append(_text(ml + 91, mt - 6, "trapped", MUTED, 9))
    return _svg(W, H, "".join(parts), f"{symbol} chip distribution")


# --------------------------------------------------------------------------- #
# 3) Signal gauge dashboard
# --------------------------------------------------------------------------- #

def _meter(x0, y0, w, label, value, vmin, vmax, bands, fmt="{:.0f}"):
    """One horizontal meter: colored zone bands + a marker at `value`."""
    parts = [_text(x0, y0 - 6, label, MUTED, 10)]
    track_y = y0 + 4
    sc = _scaler(vmin, vmax, x0, x0 + w)
    for (b0, b1, col) in bands:
        parts.append(_rect(sc(b0), track_y, sc(b1) - sc(b0), 8, col, opacity=0.35, rx=2))
    if value is not None:
        vx = sc(max(vmin, min(vmax, value)))
        parts.append(_rect(vx - 1.5, track_y - 3, 3, 14, TEXT, rx=1))
        parts.append(_text(x0 + w + 6, track_y + 8, fmt.format(value), TEXT, 10, mono=True))
    else:
        parts.append(_text(x0 + w + 6, track_y + 8, "n/a", MUTED, 10, mono=True))
    return "".join(parts)


def _badge(x0, y0, label, state, col):
    w = 150
    parts = [_rect(x0, y0, w, 22, PANEL, rx=4, stroke=AXIS)]
    parts.append(_text(x0 + 8, y0 + 15, label, MUTED, 10))
    parts.append(_text(x0 + w - 8, y0 + 15, state, col, 10, "end", weight="700", mono=True))
    return "".join(parts)


def render_gauges(symbol, indi):
    """Compact momentum/trend dashboard — RSI, Stochastic, ADX, relative volume as
    meters, plus trend / MACD / OBV / scaffold badges."""
    W, H = 480, 300
    parts = [_text(16, 22, f"{symbol} — signal dashboard", TEXT, 14, weight="700")]

    mom = indi.get("momentum") or {}
    trend = indi.get("trend") or {}
    vol = (indi.get("volume") or {}).get("relative") or {}
    x0, w = 16, 250      # meter width leaves room for the badge column at bx=310
    yy = 54

    rsi = mom.get("rsi_14")
    parts.append(_meter(x0, yy, w, "RSI (14)", rsi, 0, 100,
                        [(0, 30, SUPPORT), (30, 70, GRID), (70, 100, RESIST)]))
    yy += 40
    stoch = (mom.get("stochastic") or {}).get("k")
    parts.append(_meter(x0, yy, w, "Stochastic %K", stoch, 0, 100,
                        [(0, 20, SUPPORT), (20, 80, GRID), (80, 100, RESIST)]))
    yy += 40
    adxd = trend.get("adx") or {}
    parts.append(_meter(x0, yy, w, "ADX (trend strength)", adxd.get("adx"), 0, 60,
                        [(0, 20, GRID), (20, 25, SMA20), (25, 60, SMA50)]))
    yy += 40
    rel = vol.get("rel_volume")
    parts.append(_meter(x0, yy, w, "Relative volume", rel, 0, 3,
                        [(0, 0.6, GRID), (0.6, 1.5, SMA50), (1.5, 3, SMA20)],
                        fmt="{:.2f}x"))

    # right-column badges
    bx, by = 310, 40
    price = indi.get("price")
    s50 = trend.get("sma_50"); s200 = trend.get("sma_200")
    if s50 and s200:
        st = "UP" if s50 > s200 else "DOWN"
        parts.append(_badge(bx, by, "Primary trend", st, UP if st == "UP" else DOWN)); by += 28
    if price and s50:
        st = "ABOVE" if price > s50 else "BELOW"
        parts.append(_badge(bx, by, "vs SMA50", st, UP if st == "ABOVE" else DOWN)); by += 28
    macd = mom.get("macd") or {}
    if macd:
        st = macd.get("cross", "-").upper()
        parts.append(_badge(bx, by, "MACD", st, UP if st == "BULLISH" else DOWN)); by += 28
    obv = (indi.get("volume") or {}).get("obv") or {}
    if obv.get("trend"):
        st = obv["trend"].upper()
        parts.append(_badge(bx, by, "OBV", st, UP if st == "ACCUMULATION" else DOWN)); by += 28
    plan = indi.get("trade_scaffold") or {}
    if plan.get("reward_risk"):
        rr = plan["reward_risk"]
        parts.append(_badge(bx, by, "Scaffold RR", f"{rr}:1", UP if rr >= 2 else MUTED)); by += 28

    return _svg(W, H, "".join(parts), f"{symbol} signals")


# --------------------------------------------------------------------------- #
# Inline unicode sparkline (for watchlist one-liners)
# --------------------------------------------------------------------------- #

_SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values, n=32):
    vals = [v for v in values if isinstance(v, (int, float))][-n:]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return _SPARK[0] * len(vals)
    return "".join(_SPARK[min(len(_SPARK) - 1, int((v - lo) / (hi - lo) * (len(_SPARK) - 1)))]
                   for v in vals)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def write_charts(bars, symbol, out_dir, price_override=None, float_shares=None,
                 date=None, which=("price", "chips", "gauges")):
    """Compute indicators + chip bins from `bars` and write the requested SVGs.
    Returns {kind: path} plus a 'markdown' embed snippet."""
    o, h, l, c, v = ind._ohlcv(bars)
    if len(c) < 15:
        return {"error": f"need >=15 bars, got {len(c)}"}
    dates = []
    for b in bars:
        d = b.get("begins_at") or b.get("date") or "" if isinstance(b, dict) else ""
        dates.append(d)
    price = price_override if price_override is not None else c[-1]
    indi = ind.build(bars, price_override=price_override, float_shares=float_shares)

    os.makedirs(out_dir, exist_ok=True)
    tag = symbol.upper()
    suffix = f"-{date}" if date else ""
    written = {}

    if "price" in which:
        svg = render_price_volume(tag, o, h, l, c, v, dates, indi, price)
        p = os.path.join(out_dir, f"{tag}{suffix}-price.svg")
        with open(p, "w") as f:
            f.write(svg)
        written["price"] = p

    if "chips" in which:
        binned = ind.chip_bins(h, l, c, v, float_shares=float_shares)
        if binned:
            centers, chips, width, _pmin = binned
            svg = render_chips(tag, centers, chips, width, price,
                               indi.get("chip_distribution"))
            p = os.path.join(out_dir, f"{tag}{suffix}-chips.svg")
            with open(p, "w") as f:
                f.write(svg)
            written["chips"] = p

    if "gauges" in which:
        svg = render_gauges(tag, indi)
        p = os.path.join(out_dir, f"{tag}{suffix}-gauges.svg")
        with open(p, "w") as f:
            f.write(svg)
        written["gauges"] = p

    # markdown embed snippet using paths relative to the reports/ dir
    def _rel(p):
        return os.path.relpath(p, os.path.dirname(os.path.dirname(p)))
    md = []
    if "price" in written:
        md.append(f"![{tag} price/volume]({_rel(written['price'])})")
    if "chips" in written or "gauges" in written:
        row = []
        if "chips" in written:
            row.append(f"![{tag} chips]({_rel(written['chips'])})")
        if "gauges" in written:
            row.append(f"![{tag} signals]({_rel(written['gauges'])})")
        md.append(" ".join(row))
    written["markdown"] = "\n\n".join(md)
    written["summary"] = indi.get("summary", "")
    return written


def main():
    p = argparse.ArgumentParser(description="Render SVG charts from historicals.")
    p.add_argument("source", help="historicals JSON file, or '-' for stdin")
    p.add_argument("--symbol", required=True, help="ticker for titles/filenames")
    p.add_argument("--price", type=float, default=None, help="live price override")
    p.add_argument("--float", type=float, default=None, dest="float_shares",
                   help="circulating float (shares) for the exact chip distribution")
    p.add_argument("--out", default=".", help="output directory for the .svg files")
    p.add_argument("--date", default=None, help="date tag for filenames (YYYY-MM-DD)")
    p.add_argument("--only", default=None,
                   help="comma list subset of: price,chips,gauges")
    args = p.parse_args()

    raw = sys.stdin.read() if args.source == "-" else open(args.source).read()
    bars = ind._find_bars(json.loads(raw))
    if not bars:
        print(json.dumps({"error": "could not locate price bars in input"}))
        sys.exit(1)
    which = tuple(x.strip() for x in args.only.split(",")) if args.only else \
        ("price", "chips", "gauges")
    out = write_charts(bars, args.symbol, args.out, price_override=args.price,
                       float_shares=args.float_shares, date=args.date, which=which)
    if "error" in out:
        print(json.dumps(out)); sys.exit(1)
    for k in ("price", "chips", "gauges"):
        if k in out:
            print(out[k])
    print("\n--- markdown embed ---")
    print(out["markdown"])


if __name__ == "__main__":
    main()
