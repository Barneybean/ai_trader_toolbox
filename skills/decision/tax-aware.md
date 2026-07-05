# Tax-Aware Trading

The tradable account (configured in `config.local.toml`) is assumed to be a **taxable individual brokerage account**, so realized gains and losses have real tax consequences. Taxes are a cost like any other — the desk optimizes **after-tax** returns. General framework, not tax advice; exact rates depend on income and filing status, so the user should confirm specifics with a professional.

## Core facts

- **Holding period matters a lot.** Held **≤1 year → short-term gain, ordinary income** (higher rate). Held **>1 year → long-term gain, lower rate.** Often 10–20+ percentage points of the gain — the single biggest tax lever.
- **Match gains and losses by type.** Short-term losses first offset short-term gains; long-term losses offset long-term gains; net the two after. Realized net losses can offset up to **$3,000** of ordinary income per year, remainder carried forward.
- **Wash-sale rule.** Sell at a loss and buy the *same or substantially identical* security within **30 days before or after** → the loss is **disallowed** for now (added to the replacement's cost basis; holding period carries over). Don't harvest and jump right back in; wait 31+ days or use a genuinely different instrument.
- **Retirement accounts are different.** IRAs (Roth/Traditional) are tax-sheltered — churn there has no immediate tax cost. This desk trades the *taxable* account, so tax-awareness is fully in force. If trades route to a sheltered IRA, relax the constraints.

## How the sleeves handle tax

**Core (long-term).** Where tax optimization pays off most.
- Bias toward holding winners **past the one-year mark** when the thesis is intact. A Core winner within a couple months of long-term treatment is a strong reason *not* to sell early — quantify the difference and surface it. Only override for a genuine thesis break or risk event.
- When trimming, prefer lots already long-term, or losers to harvest.

**Tactical (short-term).** Inherently short-term / ordinary-income taxed and higher-churn, so built-in tax drag.
- Because of it, Tactical must clear a **higher gross edge** (rubric's net-edge rule). A swing that nets a hair after ordinary-income tax and spread isn't worth the risk.
- Keep Tactical the smaller allocation, consistent with its higher friction.

## Tax-loss harvesting (opportunistic)

When a holding is a loser whose thesis has weakened:
- Realizing the loss offsets realized gains (short vs long matched by type) and up to $3,000 of ordinary income — a real, bankable benefit.
- **Respect the wash-sale rule:** don't rebuy that ticker (or a substantially identical one) for 31+ days. To stay exposed to the theme, rotate into a *different* name/ETF in the same area.
- Track any ticker sold at a loss so the desk doesn't recommend rebuying inside the 30-day window (which voids the harvest).

## Rules the desk enforces

1. **Before any SELL**, state the tax character: short- or long-term? Approximate difference between selling now vs waiting for long-term? Would a loss sale trigger a wash sale given recent buys?
2. **Never recommend rebuying a loss-harvested ticker within 30 days.** Keep a short "recently harvested" list per run.
3. **Fold tax in, don't let it override risk.** A tax reason to hold never outranks a stop-loss or real thesis break — avoiding a big loss beats saving on tax. Tax is a tiebreaker/optimizer, not a reason to ride a loser ("don't let the tax tail wag the investment dog").
4. **Report the after-tax framing** on Core exits and any recommendation where tax materially changes the picture.

## Quick reference

| Situation | Tax-aware move |
|---|---|
| Core winner near 1-yr mark, thesis intact | Prefer to hold for long-term rate; quantify the saving |
| Position stopped out / thesis broken | Exit regardless of tax — risk first |
| Losing position, weak thesis, have gains to offset | Consider harvesting; avoid rebuy 31+ days |
| Want to rotate but both names similar rank | Don't — turnover costs tax; hold (see skills/decision/strategies.md) |
| Tactical (short-term) idea with thin edge | Skip — ordinary-income tax + spread eats it |

