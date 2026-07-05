# Options Playbook — Preferred Structures

The user trades options and prefers defined, income-oriented structures. Capture these as
sanctioned strategies the desk proposes *when appropriate*, with the same confirm-before-place
discipline as equities.

## ⚠️ Account constraint (check first)

Options require an approved **option level** on the traded account. The desk reads which account it
may trade — and any option-level limits — from local config (`config.local.toml`, git-ignored) and
by calling `get_accounts` each run; account numbers are **never** hardcoded here. Handle:
- Tradable account has **no option level** → **cannot place options there**; may still
  analyze/recommend and tell the user to enable options or place manually.
- Options-approved account isn't the agent-accessible one → can't route orders to it.
- **Cash accounts** can't do margin strategies (e.g., naked puts need the cash-secured form).

Re-check `get_accounts` each run; respect whatever the live account allows.

## Core concepts the user uses

- **Delta** ≈ sensitivity to the underlying and a rough proxy for probability of finishing ITM.
  Higher delta = more stock-like, higher cost, higher assignment odds.
- **Buy in-the-money (ITM) options** for stock-like exposure with less time-premium decay and higher
  delta — the user's preference for directional bets.

## Sanctioned structures

### Covered call
Own 100 shares, sell a call against them for premium. **Use when willing to sell the shares at the
strike and wanting income, accepting capped upside.** Best on Core names that have run up where the
user would happily be called away near resistance. Premium lowers effective cost basis; the
trade-off caps gains above the strike.

### Cash-secured put (sell put)
Sell a put, set aside cash to buy if assigned. **Use to get paid to potentially buy a stock you want
lower.** Premium reduces effective entry. Risk is substantial if the stock falls hard (obligated to
buy at the strike) but defined by strike minus premium; the *cash-secured* form for a cash account,
not a naked put. Size so assignment wouldn't blow the per-idea risk cap.

### Vertical spreads (call or put)
Buy one option, sell another of the same type at a different strike/same expiry to **cap both cost
and risk**. The user's tool for a directional view with defined, limited loss (reference the user's
noted resource: youtu.be/1SVswX2V_vE). Prefer over naked long options when paying up for premium,
and over naked short options when risk must be bounded.

## How the desk proposes options

1. **Only when the structure fits thesis and horizon** — covered calls/CSPs for income and entries
   on names you'd hold; verticals for defined-risk directional bets. Don't bolt options onto every
   idea.
2. **Always show:** structure, strikes, expiry, net debit/credit, max gain, max loss, breakeven,
   assignment implications — options hide risk that must be explicit.
3. **Respect the account constraint above**; flag when the trade can't be placed in the tradable
   account as-is.
4. **Tax note:** most options are short-term / ordinary-income taxed; covered-call premium and
   assignments have their own treatment — keep Tactical-sleeve tax drag in mind
   (`skills/decision/tax-aware.md`).
5. **Confirm before placing** via `review_option_order` → explicit yes → `place_option_order`, same
   as equities.

**Mentor's options discipline** (`skills/playbook/mentor-casebook.md`): only **small, LONG-dated
calls on high-conviction names** — a tiny position (≲0.15–1%) on a multi-quarter/year thesis (his RC
Jan-2027, SOFI, Google/Intel calls — all taken to profit). **Short-dated options = gambling**
("玩多了长期都亏钱") — avoid. Use puts only as brief tactical hedges at highs, taken to profit in days,
not as a standing book.

