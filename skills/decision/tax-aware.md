# Tax-Aware Trading

Read the account's tax treatment from local configuration or ask the user. Never infer that an
account is taxable, tax-advantaged, or subject to one jurisdiction's rules. Apply this framework
only where it matches the user's account and location. Taxes are a cost like any other, but this is
general education—not tax advice; the user should confirm specifics with a professional.

## Core facts

- **Holding period matters a lot.** Held **≤1 year → short-term gain, ordinary income** (higher rate). Held **>1 year → long-term gain, lower rate.** Often 10–20+ percentage points of the gain — the single biggest tax lever.
- **Match gains and losses by type.** Short-term losses first offset short-term gains; long-term losses offset long-term gains; net the two after. Realized net losses can offset up to **$3,000** of ordinary income per year, remainder carried forward.
- **Wash-sale rule.** Sell at a loss and buy the *same or substantially identical* security within **30 days before or after** → the loss is **disallowed** for now (added to the replacement's cost basis; holding period carries over). Don't harvest and jump right back in; wait 31+ days or use a genuinely different instrument.
- **Tax-advantaged accounts are different.** Their treatment varies by jurisdiction and account
  type. Apply taxable-account constraints only when the configured execution account is taxable.

## How the sleeves handle tax

**Core (long-term).** Where tax optimization pays off most.
- Bias toward holding winners **past the one-year mark** when the thesis is intact. A Core winner within a couple months of long-term treatment is a strong reason *not* to sell early — quantify the difference and surface it. Only override for a genuine thesis break or risk event.
- When trimming, prefer lots already long-term, or losers to harvest.

**Tactical (short-term).** Inherently short-term / ordinary-income taxed and higher-churn, so built-in tax drag.
- Because of it, Tactical must clear a **higher gross edge** (rubric's net-edge rule). A swing that nets a hair after ordinary-income tax and spread isn't worth the risk.
- Keep Tactical the smaller allocation, consistent with its higher friction.

## Tax-loss harvesting — the harvest-and-replace protocol

*(Terminology guard: a **wash sale** is this tax rule. A **chip wash / 洗盘** in
`skills/analysis/chip-distribution.md` is an unrelated price-action concept — never conflate them.)*

When a holding is a loser whose thesis has weakened, don't just sell — harvest, then **choose the
re-entry path by prediction**:

- **Path A — replace (default when the theme is still live):** rotate into a good same-industry
  name/ETF so exposure never lapses. Use when the desk expects the theme to move within the window.
- **Path B — wait out the window and rebuy the same stock:** stay in cash 31+ days, then rebuy,
  when the desk's *prediction for the next ~5 weeks* says the stock is unlikely to run — e.g. it's
  in markdown/early basing with more washes expected, no catalyst (earnings, FDA, product event)
  falls inside the window, and the entry is expected at-or-below today's price. This banks the
  loss AND keeps the original name at a similar or better basis. The explicit risk being accepted:
  a surprise gap-up inside the window is missed — so Path B requires a stated phase/timing call
  (`skills/analysis/chip-distribution.md`), not hope. The catalyst check is not a guess:
  run `skills/analysis/catalyst-scan.md` (earnings calendar, ex-div, regulatory dates, debt
  maturities from the filings) and cite the clear calendar. If a catalyst sits inside the
  31 days, Path B is disqualified — replace instead, or accept holding through it knowingly.

**Path A mechanics:**

1. **Pick the replacement BEFORE selling.** A *good* stock in the **same industry/theme** —
   sourced from the desk's own rankings (`skills/analysis/sectors/*`, current watchlists), not a
   random peer. Criteria: keeps the thematic exposure the original provided, desk-rated equal or
   better on fundamentals/setup, liquid enough to exit, and **not substantially identical** to
   what was sold. Ideally the replacement is a name the desk already wanted to own — a harvest is
   a free chance to upgrade the position. Default fallback when no single name clears the bar: a
   **broad sector/theme ETF** (clearly not substantially identical) as a 31-day placeholder.
2. **Execute as a pair** — sell the loser and buy the replacement the same session, so the
   portfolio is never out of the theme (missing a 5% theme rally to save 1% of tax is a bad trade).
3. **Verify the loss survives (61-day window check).** The rule spans **30 days BEFORE the sale,
   the sale day, and 30 days after**. Before selling, check the last 30 days of fills
   (`get_equity_orders` / P&L history) for buys of the same ticker — recent DCA adds or dividend
   reinvestment inside the window partially void the harvest. Then make sure nothing rebuys it
   for 31+ days: cancel open limit orders on the ticker, pause any DCA on it.
4. **"Substantially identical" in practice:** the same ticker, other share classes of the same
   company, and options/deep-ITM calls on it are inside the rule. An **industry peer or a
   sector ETF is fine** — that's exactly why harvest-and-replace works. Two ETFs tracking the
   *same index* are risky; use a different-index fund.
5. **Journal it.** Log every harvest in `journal/decisions.jsonl` with ticker, sale date, loss
   realized, path chosen (replacement bought, or wait-and-rebuy with the timing thesis), and the
   **window-end date (sale + 31 days)**. Every desk run reads this list, hard-blocks rebuy
   recommendations inside the window, and — for Path B names — surfaces "window opens <date>,
   re-check entry" as an action item once it passes.
6. **After day 31 — reassess, don't reflex-swap.** Return to the original only if it *still*
   ranks above the replacement; often the replacement was the better stock (that's why it was
   chosen) and the swap-back just adds friction. If swapping back, mind the new gain/loss on the
   replacement leg.

The benefit: the realized loss offsets gains (matched by type) plus up to $3,000 of ordinary
income, the excess carries forward — banked while the theme exposure never lapsed.

## Rules the desk enforces

1. **Before any SELL**, state the tax character: short- or long-term? Approximate difference between selling now vs waiting for long-term? Would a loss sale trigger a wash sale given recent buys (check fills 30 days back — the window reaches *backward* too)?
2. **Never recommend rebuying a loss-harvested ticker (or substantially identical instrument) within the 31-day window.** Check the journal's harvest log at the start of every run; cancel/flag open orders and DCA that would violate it.
3. **Every loss sale states its re-entry path**: same-industry replacement (Path A), wait-out-the-window-and-rebuy with the timing prediction that justifies it (Path B), or an explicit "stay out — the whole theme is broken." Harvesting exposure away by accident is a silent cost.
3. **Fold tax in, don't let it override risk.** A tax reason to hold never outranks a stop-loss or real thesis break — avoiding a big loss beats saving on tax. Tax is a tiebreaker/optimizer, not a reason to ride a loser ("don't let the tax tail wag the investment dog").
4. **Report the after-tax framing** on Core exits and any recommendation where tax materially changes the picture.

## Quick reference

| Situation | Tax-aware move |
|---|---|
| Core winner near 1-yr mark, thesis intact | Prefer to hold for long-term rate; quantify the saving |
| Position stopped out / thesis broken | Exit regardless of tax — risk first |
| Losing position, weak thesis, have gains to offset | Harvest; replace in-industry (theme live) or wait 31 days and rebuy (no catalyst in window, entry expected flat/lower) |
| Want to rotate but both names similar rank | Don't — turnover costs tax; hold (see skills/decision/strategies.md) |
| Tactical (short-term) idea with thin edge | Skip — ordinary-income tax + spread eats it |
