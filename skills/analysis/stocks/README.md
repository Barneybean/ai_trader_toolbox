# Stock playbooks — coverage map

The commons' **single-name altitude**: one playbook per ticker, capturing how a *specific stock*
trades and prices — its repeating setups, catalyst calendar, valuation ranges, and dated worked
episodes. When the desk analyzes a name, it checks here for a matching `<TICKER>.md` and reads it
alongside the industry's [sector playbook](../sector-playbooks.md).

**The hard rule that makes this shareable:** a stock playbook is **dated knowledge, never a live
call.** "NVDA has sold the news on 7 of its last 9 earnings" is knowledge; "buy NVDA now" is a
position and doesn't belong in the commons. Keep live theses in
`skills/playbook/watchlist-theses.md` or your git-ignored private overlay.

## ✅ Covered

| Ticker | File | The read |
|---|---|---|
| — | *(none yet)* | |

## How to contribute one

1. Copy [`_TEMPLATE.md`](_TEMPLATE.md) → `<TICKER>.md` and answer all seven fields; link the
   sector playbook for the industry backdrop instead of repeating it.
2. Add a row to the table above.
3. Meet the same quality bar as sector playbooks
   ([`CONTRIBUTING.md`](../../../CONTRIBUTING.md#the-playbook-quality-bar)): **specific ·
   falsifiable · primary-sourced · dated · illustrated · general** — episodes must be dated
   history, and `python3 scripts/ops/scan_pii.py` must pass.

Names with rich, repeating structure work best: NVDA, TSLA, INTC, AAPL, AMD, META, COIN, MU —
anywhere the same pattern has shown up more than once.
