#!/usr/bin/env python3
"""Fetch daily OHLCV history from Yahoo Finance — pure stdlib, no pandas.

Robinhood's connector only serves ~1 year of daily bars. The forecaster's base
rates and Monte-Carlo bootstrap get materially better with a longer sample, so
this pulls multi-year history from Yahoo's public chart API and emits it in the
exact bar shape `indicators.py` / `forecast.py` / `charts.py` already parse
(a list of {begins_at, open, high, low, close, volume} dicts).

    python3 scripts/yahoo.py MP                         # 5y daily -> stdout
    python3 scripts/yahoo.py MP --range 10y --out reports/data/MP.json
    python3 scripts/yahoo.py MP --raw                   # unadjusted (actual traded prices)

Then feed the file to any of the analytics:

    python3 scripts/forecast.py reports/data/MP.json --price 53.31
    python3 scripts/indicators.py reports/data/MP.json --price 53.31

By DEFAULT the series is split/dividend back-adjusted (Yahoo `adjclose`), which
is what you want for return-based math (Monte-Carlo, base rates). Use --raw for
the actual traded prices when you care about literal historical levels / chips.

Networking note: macOS system Pythons often ship without a CA bundle, so we
verify TLS against `certifi` when it's installed and fall back to the default
SSL context otherwise. No API key; this is the same public endpoint the Yahoo
Finance charts use, so be a considerate caller (cache to a file, don't hammer).
"""
import argparse
import json
import ssl
import sys
import urllib.parse
import urllib.request

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval={iv}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Valid Yahoo range / interval tokens (guard rails; Yahoo 422s on bad tokens).
RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
INTERVALS = {"1d", "5d", "1wk", "1mo", "3mo"}


def _ssl_context():
    """Verify TLS via certifi when present, else the platform default."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch(symbol, rng="5y", interval="1d", adjusted=True, timeout=20):
    """Return a list of bar dicts (oldest first). Raises on network/parse error."""
    symbol = symbol.strip().upper()
    if rng not in RANGES:
        raise ValueError(f"bad --range {rng!r}; use one of {sorted(RANGES)}")
    if interval not in INTERVALS:
        raise ValueError(f"bad --interval {interval!r}; use one of {sorted(INTERVALS)}")
    url = CHART.format(sym=urllib.parse.quote(symbol), rng=rng, iv=interval)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        doc = json.load(r)

    chart = doc.get("chart") or {}
    if chart.get("error"):
        raise RuntimeError(f"Yahoo error for {symbol}: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise RuntimeError(f"no data returned for {symbol}")
    res = results[0]

    ts = res.get("timestamp") or []
    quote = (res.get("indicators", {}).get("quote") or [{}])[0]
    adj = (res.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
    o, h, l, c = [quote.get(k) or [] for k in ("open", "high", "low", "close")]
    vol = quote.get("volume") or []

    bars = []
    for i, t in enumerate(ts):
        close = c[i] if i < len(c) else None
        if close is None:            # Yahoo pads holidays/halts with nulls — skip them
            continue
        # Back-adjustment factor (split + dividend). ~1.0 for recent bars.
        f = (adj[i] / close) if (adjusted and adj and i < len(adj)
                                 and adj[i] is not None and close) else 1.0
        op = o[i] if i < len(o) and o[i] is not None else close
        hi = h[i] if i < len(h) and h[i] is not None else close
        lo = l[i] if i < len(l) and l[i] is not None else close
        vv = vol[i] if i < len(vol) and vol[i] is not None else 0
        bars.append({
            "begins_at": _iso(t),
            "open": round(op * f, 6),
            "high": round(hi * f, 6),
            "low": round(lo * f, 6),
            "close": round(close * f, 6),
            "volume": int(vv),
        })
    if not bars:
        raise RuntimeError(f"{symbol}: response had timestamps but no usable closes")
    return bars


def _iso(epoch):
    """UTC date string from a Unix timestamp, without touching wall-clock time
    (datetime.utcfromtimestamp is deterministic; no now()/random used anywhere)."""
    import datetime
    return datetime.datetime.utcfromtimestamp(int(epoch)).strftime("%Y-%m-%d")


def main(argv=None):
    p = argparse.ArgumentParser(description="Fetch Yahoo Finance daily OHLCV as analytics-ready JSON.")
    p.add_argument("symbol")
    p.add_argument("--range", default="5y", help=f"history window: {sorted(RANGES)} (default 5y)")
    p.add_argument("--interval", default="1d", help=f"bar size: {sorted(INTERVALS)} (default 1d)")
    p.add_argument("--raw", action="store_true",
                   help="unadjusted actual traded prices (default: split/dividend adjusted)")
    p.add_argument("--out", default=None, help="write JSON here (default: stdout)")
    a = p.parse_args(argv)

    try:
        bars = fetch(a.symbol, a.range, a.interval, adjusted=not a.raw)
    except Exception as e:
        print(f"yahoo.py: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    payload = json.dumps(bars, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        span = f"{bars[0]['begins_at']}..{bars[-1]['begins_at']}"
        print(f"Wrote {a.out}  ({len(bars)} bars, {span}, "
              f"{'raw' if a.raw else 'adjusted'})", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
