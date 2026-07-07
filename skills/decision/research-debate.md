# Structured Research Debate (Bull vs Bear, multi-round)

**What this upgrades.** The desk runs a Bull-vs-Bear Red Team (SKILL.md Step 5); this makes it a **structured, multi-round debate with an adjudicating Research Manager** — the TradingAgents mechanism that stops a thesis from winning by assertion. It does **not** replace the edge doctrine: the debate's *content* is still the `skills/edge/variant-perception.md` thesis and the `skills/decision/stress-test.md` attack. It just makes the adversarial process iterative and forces a committed verdict.

Borrowed-and-adapted from TradingAgents' researcher team + `research_manager`; subordinate to this desk's rubric, sleeves, and mentor method.

---

## Roles

- **Bull Researcher** — argues the long case on the *variant-perception statement* (not generic optimism): what the market misses, why it isn't priced, the catalyst that closes the gap. Cites specialists' evidence (fundamentals, quant levels, insider flows, wave position).
- **Bear Researcher** — argues short/avoid. Its job is the `skills/decision/stress-test.md` attack made adversarial: two-sided catalysts, the weakest load-bearing assumption, disconfirming evidence, the pre-mortem, and the consensus view the bull fades (steelmanned — you can only fade a view you fully understand).
- **Research Manager** — adjudicates and produces the **investment plan** the PM sizes.

---

## The debate protocol

1. **Rounds.** Default **2**; **3** for high-conviction/large-size, **1** for quick screens. (The desk's `max_debate_rounds` — scale to stakes, not habit.)
2. **Rebuttal rule — engage, don't restate.** After round 1, each side must **directly rebut the other's single strongest point** before adding anything new. Ignoring the opponent's best point disqualifies the argument.
3. **Evidence discipline.** Every claim ties to a dated source, an `indicators.py` number, or a filing — no vibes. Not "the chart looks strong" but "reclaimed SMA50 on 1.8× volume, OBV making highs."
4. **Convergence check.** If both sides converge (e.g. "fairly priced, no edge"), stop early and label it **beta / no variant edge** — that is the verdict.

---

## Adjudication — the Research Manager commits

Reads the full debate and issues a **committed stance on a 5-point scale**, mapped to desk actions:

| Stance | Desk action | Meaning |
|---|---|---|
| **Strong Buy** | Buy / Accumulate aggressively (within caps) | Bull decisively won; variant edge intact |
| **Buy / Overweight** | Buy / Accumulate | Bull won on balance |
| **Hold** | Watch / no trade | *Only* when evidence is genuinely balanced — not a cop-out |
| **Underweight** | Trim / avoid new | Bear won on balance |
| **Sell / Avoid** | Trim/exit or do-not-buy | Bear decisively won |

**Do not default to Hold** — commit whenever the strongest arguments warrant it; Hold is for genuine stalemate, not indecision.

**Output — the Investment Plan** (feeds SKILL.md Step 6, PM/Trader):
- Committed stance + the **one argument that decided it** (which strongest point won, why the other's best rebuttal failed).
- The surviving **variant-perception statement** (or note it collapsed to consensus → cut/beta).
- The **1–2 questions the thesis is still most vulnerable on** (to Risk).
- Provisional horizon read: short-run and long-run calls (two-horizon rule).

---

## Guardrails

- The debate **serves** the CIO gate and rubric, doesn't replace them. A Strong-Buy still clears every hard gate in `skills/decision/review-rubric.md` (RR ≥ 2, defined invalidation, sleeve-appropriate edge, conviction ≥ Medium).
- The bear's attack **is** the `skills/decision/stress-test.md` — don't run them separately; the stress-test is the bear's ammunition.
- Keep the desk's voice: variant perception, secular-wave position, chip/phase read, and the mentor's "buy weakness in quality" lens are the *substance* debated. This is the ring; the edge doctrine is the fighter.
