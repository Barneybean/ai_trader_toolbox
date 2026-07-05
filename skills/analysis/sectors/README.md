# Sector playbooks — coverage map & wanted list

This folder is the desk's **industry brain** — one playbook per sector, each answering what a
specialist would ask (see [`_TEMPLATE.md`](_TEMPLATE.md)). It is also the heart of the project's
**knowledge commons**: playbooks are contributed by people who actually know the industry,
reviewed in the open against a named quality bar, and read by every desk built on this repo.

## ✅ Covered

| Sector | File | Prices on… |
|---|---|---|
| Semiconductors & hardware | [`semiconductors.md`](semiconductors.md) | node yield, memory cycle & contracts, design wins |
| Biotech & pharma | [`biotech-pharma.md`](biotech-pharma.md) | pipeline rNPV, cash runway, trial/PDUFA catalysts |
| Software / AI / internet | [`software-ai.md`](software-ai.md) | growth durability, NRR, AI monetization, Rule of 40 |
| Consumer fintech / product-led | [`consumer-fintech.md`](consumer-fintech.md) | product-led flywheel, stickiness, ecosystem |
| Nuclear / power / energy | [`power-energy-nuclear.md`](power-energy-nuclear.md) | licensing/timeline, PPAs, AI power demand |
| Robotics / autonomy | [`robotics-autonomy.md`](robotics-autonomy.md) | deployment scale, unit economics (optionality) |

## 🙏 Most wanted

If you've worked in or seriously traded one of these, an hour of your knowledge gives every desk
downstream a specialist it didn't have. Claim one by opening a **playbook proposal** issue.

| Sector | The read a generalist misses | Status |
|---|---|---|
| Banks & insurance | rate sensitivity, credit cycle, book-value quality | **open** |
| REITs & real estate | cap rates, FFO, refinancing walls | **open** |
| Oil & gas / midstream | strip prices, breakevens, reserve life | **open** |
| Mining & materials | commodity cycle, AISC, grades & permitting | **open** |
| Industrials & defense | backlog / book-to-bill, program cycles | **open** |
| Healthcare services & medtech | reimbursement, utilization, regulatory path | **open** |
| Retail & consumer staples | comps, inventory turns, private-label pressure | **open** |
| Media, gaming & internet ads | engagement, ARPU, content cycles | **open** |
| Autos & EV supply chain | production ramps, battery costs, ASP/mix | **open** |
| Airlines, travel & lodging | RASM/CASM, load factors, booking curves | **open** |
| Agriculture & food | crop cycles, input costs, USDA reports | **open** |
| Crypto-adjacent equities | correlation regimes, treasury exposure, halving cycles | **open** |

Sectors we haven't listed are just as welcome — the table grows with the commons.

## How to contribute one

1. Copy [`_TEMPLATE.md`](_TEMPLATE.md) → `<sector>.md` and answer **all seven fields** — what sets
   the price, catalysts + primary sources, valuation lens, red flags, sources, a worked archetype,
   and the variant angle.
2. Register it: add a row to [`../sector-playbooks.md`](../sector-playbooks.md) and move the row
   here from *wanted* to *covered*.
3. Meet the quality bar in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#the-playbook-quality-bar):
   **specific · falsifiable · primary-sourced · dated · illustrated · general.**
4. `python3 scripts/scan_pii.py` must pass — share the craft, never your positions or anything you
   don't have the right to publish.
