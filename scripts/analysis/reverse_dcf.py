#!/usr/bin/env python3
"""Reverse DCF + three-scenario valuation (ai-berkshire style; no LLM mental math).

Reverse mode (default): solve the FCF growth rate the CURRENT price implies,
so an extended "definer" is exposed by one number ("price implies 28%/yr for 10y").
  PV = sum_{t=1..N} FCF0*(1+g)^t/(1+r)^t  +  FCF0*(1+g)^N*(1+gT)/((r-gT)*(1+r)^N)
solved for g by bisection so PV = market cap.

Scenario mode: fair-value range from explicit growth + exit multiples
(optimistic/base/pessimistic), per ai-berkshire's three-scenario requirement.

Usage:
  # what growth does the price imply?
  python3 scripts/analysis/reverse_dcf.py --mcap 390e9 --fcf 11e9
  python3 scripts/analysis/reverse_dcf.py --price 140.27 --shares 2.8e9 --fcf 11e9 --discount 0.10

  # three-scenario fair value (growth for N years, then exit multiple on FCF)
  python3 scripts/analysis/reverse_dcf.py --fcf 11e9 --shares 2.8e9 --scenarios 0.20:25 0.12:18 0.05:12

All cash-flow figures must come from primary sources (10-K/press release) —
this script only does the arithmetic; it does not fetch fundamentals.
"""
import argparse
import sys


def pv_of_growth(fcf0, g, r, gt, years):
    pv = 0.0
    f = fcf0
    for t in range(1, years + 1):
        f = fcf0 * (1 + g) ** t
        pv += f / (1 + r) ** t
    if r <= gt:
        raise ValueError("discount rate must exceed terminal growth")
    terminal = f * (1 + gt) / (r - gt)
    return pv + terminal / (1 + r) ** years


def implied_growth(mcap, fcf0, r, gt, years):
    lo, hi = -0.50, 1.50
    if pv_of_growth(fcf0, lo, r, gt, years) > mcap:
        return lo  # price implies worse than -50%/yr
    if pv_of_growth(fcf0, hi, r, gt, years) < mcap:
        return hi
    for _ in range(200):
        mid = (lo + hi) / 2
        if pv_of_growth(fcf0, mid, r, gt, years) < mcap:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fcf", type=float, required=True, help="TTM free cash flow, $ (e.g. 11e9)")
    ap.add_argument("--mcap", type=float, help="market cap, $")
    ap.add_argument("--price", type=float, help="share price (with --shares)")
    ap.add_argument("--shares", type=float, help="shares outstanding")
    ap.add_argument("--discount", type=float, default=0.10, help="discount rate (default 0.10)")
    ap.add_argument("--terminal", type=float, default=0.025, help="terminal growth (default 0.025)")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--scenarios", nargs="*", metavar="G:MULT",
                    help="scenario mode: growth:exit-multiple pairs, e.g. 0.20:25 0.12:18 0.05:12")
    args = ap.parse_args()

    mcap = args.mcap
    if mcap is None and args.price and args.shares:
        mcap = args.price * args.shares

    if args.scenarios:
        if not args.shares:
            print("scenario mode needs --shares for per-share values", file=sys.stderr)
            return 1
        labels = ["optimistic", "base", "pessimistic"]
        print(f"THREE-SCENARIO VALUATION  (FCF ${args.fcf:,.0f} · {args.years}y · discount {args.discount:.0%})")
        for i, spec in enumerate(args.scenarios):
            try:
                g, mult = spec.split(":")
                g, mult = float(g), float(mult)
            except ValueError:
                print(f"bad scenario {spec!r} — expected growth:exit_multiple, e.g. 0.20:25",
                      file=sys.stderr)
                return 1
            fcf_n = args.fcf * (1 + g) ** args.years
            value = 0.0
            for t in range(1, args.years + 1):
                value += args.fcf * (1 + g) ** t / (1 + args.discount) ** t
            value += fcf_n * mult / (1 + args.discount) ** args.years
            label = labels[i] if i < len(labels) else f"scenario{i+1}"
            line = f"  {label:<12} growth {g:+.0%}/yr, exit {mult:.0f}x FCF  ->  ${value/args.shares:,.2f}/sh"
            if args.price:
                line += f"  ({(value/args.shares/args.price - 1)*100:+.0f}% vs ${args.price})"
            print(line)
        return 0

    if mcap is None:
        print("need --mcap, or --price with --shares", file=sys.stderr)
        return 1
    g = implied_growth(mcap, args.fcf, args.discount, args.terminal, args.years)
    fcf_yield = args.fcf / mcap
    print(f"REVERSE DCF  (mcap ${mcap:,.0f} · FCF ${args.fcf:,.0f} · FCF yield {fcf_yield:.1%})")
    print(f"  price implies FCF growth of {g:+.1%}/yr for {args.years} years")
    print(f"  (discount {args.discount:.0%}, terminal growth {args.terminal:.1%})")
    if g >= 0.25:
        print("  read: VERY demanding — only elite compounders have delivered this; a 'hold' needs justification")
    elif g >= 0.15:
        print("  read: demanding — plausible for a definer mid-wave, but check vs actual growth rate")
    elif g >= 0.05:
        print("  read: reasonable — market pricing moderate growth")
    else:
        print("  read: pessimistic — market pricing stagnation/decline; potential value if thesis says otherwise")
    return 0


if __name__ == "__main__":
    sys.exit(main())
