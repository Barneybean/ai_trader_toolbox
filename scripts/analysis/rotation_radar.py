#!/usr/bin/env python3
"""Rotation radar — notice a sector cracking (or turning) before the crowd does.

Codifies the mentor's highest-value behavior: he de-risked the AI-semi complex BEFORE the
July-2026 tech selloff and had already rotated into healthcare/defensives (his trims fell
6-19% while MRNA/JNJ ripped). The tell is almost always RELATIVE: a sector still "up big"
whose recent relative strength has quietly flipped negative, while a neglected sector's
relative strength turns positive off a base.

    python3 scripts/analysis/rotation_radar.py            # sector ETF sweep vs SPY
    python3 scripts/analysis/rotation_radar.py QQQ SMH …  # custom universe

Per sector ETF (2y daily, via scripts/lib/yahoo.py):
  RS63 / RS21 — 63d and 21d return minus SPY's (medium vs recent relative strength)
  %52wH       — distance below the 52-week high
  BBpct       — Bollinger-width percentile of its own 2y history (extension/coil gauge)

Labels:
  EXTENDED   RS63 strongly +, near highs, width stretched — crowded; trim-into-strength zone
  COOLING    RS63 + but RS21 flipped − — the early crack (the mentor signal); start trimming
  TURNING    RS63 − but RS21 flipped + off a base — early rotation destination
  NEGLECTED  RS63 and RS21 − , far from highs — hunting ground, needs a catalyst
  NEUTRAL    nothing loud

Output is a map, not an order: pair with the base-position rule
(`skills/edge/thematic-waves.md`) — rotation calls TRIM TO A BASE, never to zero.
"""
import os
import statistics
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_SCRIPTS, d) for d in ("lib", "analysis", "ops")]
from yahoo import fetch  # noqa: E402

SECTORS = {
    "XLK": "tech", "SMH": "semis", "XLV": "health", "IBB": "biotech", "XLF": "financials",
    "XLE": "energy", "XLI": "industrials", "XLP": "staples", "XLY": "discretionary",
    "XLU": "utilities", "XLRE": "reits", "XRT": "retail",
}


def closes(sym):
    return [b["close"] for b in fetch(sym, "2y", "1d") if b.get("close")]


def ret(px, n):
    # None (not a fake 0.0) when history is too short — a fabricated relative
    # strength on a recent listing is worse than an honest gap
    return 100.0 * (px[-1] / px[-1 - n] - 1) if len(px) > n else None


def bb_width_pct(px, win=20):
    widths = []
    for i in range(win, len(px) + 1):
        w = px[i - win:i]
        m = statistics.fmean(w)
        widths.append(4 * statistics.pstdev(w) / m if m else 0)
    cur = widths[-1]
    return 100.0 * sum(1 for w in widths if w <= cur) / len(widths)


def label(rs63, rs21, off_hi, bbp):
    # COOLING first: the mentor signal is the early crack while still near the
    # highs — a name can qualify for both, and EXTENDED must not mask it
    if rs63 > 2 and rs21 < -1:
        return "COOLING"
    if rs63 > 3 and off_hi > -5 and bbp > 75:
        return "EXTENDED"
    if rs63 < -2 and rs21 > 1:
        return "TURNING"
    if rs63 < -3 and rs21 < 0:
        return "NEGLECTED"
    return "NEUTRAL"


def main():
    universe = sys.argv[1:] or list(SECTORS)
    spy = closes("SPY")
    s63, s21 = ret(spy, 63), ret(spy, 21)
    rows = []
    for sym in universe:
        try:
            px = closes(sym)
        except Exception as e:
            print(f"  {sym}: fetch failed ({e})", file=sys.stderr)
            continue
        r63, r21 = ret(px, 63), ret(px, 21)
        if len(px) < 64 or r63 is None or r21 is None or s63 is None or s21 is None:
            print(f"  {sym}: skipped — only {len(px)} bars (need 64+ for RS63)", file=sys.stderr)
            continue
        rs63, rs21 = r63 - s63, r21 - s21
        off_hi = 100.0 * (px[-1] / max(px[-252:]) - 1)
        bbp = bb_width_pct(px)
        rows.append((label(rs63, rs21, off_hi, bbp), sym, SECTORS.get(sym, ""), rs63, rs21, off_hi, bbp))

    order = {"COOLING": 0, "EXTENDED": 1, "TURNING": 2, "NEGLECTED": 3, "NEUTRAL": 4}
    rows.sort(key=lambda r: (order[r[0]], -abs(r[3])))
    print(f"SPY 63d {s63:+.1f}% / 21d {s21:+.1f}%   (RS = sector return minus SPY)")
    print(f"{'LABEL':<11}{'ETF':<6}{'sector':<14}{'RS63':>7}{'RS21':>7}{'%52wH':>8}{'BBpct':>7}")
    for lab, sym, name, rs63, rs21, off, bbp in rows:
        print(f"{lab:<11}{sym:<6}{name:<14}{rs63:>+6.1f}%{rs21:>+6.1f}%{off:>+7.1f}%{bbp:>6.0f}%")
    print("\nCOOLING = the mentor signal (crack before the headline) -> trim leaders TO A BASE."
          "\nTURNING/NEGLECTED = rotation destinations -> prefer weakness; buy strength only if the continuation gate passes.")


if __name__ == "__main__":
    main()
