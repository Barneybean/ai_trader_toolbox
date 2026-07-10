# The Sufficiency Gate — "have you done enough work to say this?"

Every gate in this desk tests the *logic* of a thesis (stress-test, Red Team, Risk, CIO). This one
tests its **evidence base**. Before ANY actionable recommendation ships — buy, sell, trim, a changed
stop, a reversed stance — a reviewer (a fresh pass, ideally a fresh agent not invested in the
conclusion) must ask, verbatim:

> **"Have you collected enough information and done enough quant analysis to come up with this
> recommendation?"**

If the honest answer is no on any item below, the recommendation does not ship. It either goes back
for the missing work, or ships explicitly labeled **"preliminary — not actionable"** with the gaps
named. "The user asked for an answer tonight" is not an exemption — a wrong recommendation delivered
fast is the most expensive product this desk makes.

**Scope: everything actionable.** Full desk runs already pass Steps 5–8; this gate closes the hole
those steps don't cover — the *ad-hoc advisory* ("should I adjust X?", "what do you think of Y?")
answered outside the pipeline. An advisory that names an action IS a recommendation and passes this
gate. Watch/hold reaffirmations with no action change may ship on inline judgment.

---

## The case that created this gate (keep it here — it's the calibration)

**MRVL, July 2026.** An ad-hoc advisory recommended trimming a long-held Marvell position on an
"AWS socket lost" thesis. The user asked one question — *"are you sure?"* — and an adversarial
verification pass flipped the call to HOLD within the hour:

- The load-bearing fact (Trainium3 back-end → Alchip) was **seven months old**, still unconfirmed by
  either company, and the stock had **tripled through it** — it was priced, not edge.
- The research pass **missed the strongest opposing fact**: Microsoft Maia 300 was a live Marvell
  program ramping Q4 2026 (~$10–12B 2027 revenue potential).
- The pullback being "explained" by the stale fact was actually index-flow unwind + insider sales +
  valuation + sector rout — **no current analyst cited AWS**.
- The freshest tape (same-day RBC $360 reiteration, UBS raise to $340) **leaned against the call**
  and wasn't checked.
- The quant read **cherry-picked**: flow-pressure distribution was cited; the same engine suite's
  OBV accumulation read was omitted.

Every one of those five failures is now a named checklist item. The gate exists so the *reviewer*
asks "are you sure?" before the user has to.

---

## The checklist

### A. Information sufficiency

1. **Every load-bearing fact is dated and sourced** — and for each, answer the **priced-in check**:
   what has the stock done *since* that fact broke? A fact the price has already fully traversed
   (tripled through, crashed through) is context, not edge. If the thesis dies without a fact older
   than one quarter, that fact needs a fresh re-verification before it can carry weight.
2. **The freshest tape was checked** — last 72 hours of news, analyst actions, and filings. State
   explicitly whether it leans **with or against** the call. A call that contradicts same-week
   sell-side action isn't necessarily wrong, but shipping it without knowing is.
3. **Evidence is tiered**: company filings/statements > customer artifacts/patents > sell-side >
   media > social. A supply-chain / design-win / socket claim that **neither company has confirmed
   is rumor-tier** — it may inform, it may not decide.
4. **The strongest opposing fact was actively hunted and is named in the thesis.** Not "risks
   exist" — the single specific fact that most damages the call, found by searching for it as hard
   as the confirming set was searched for. If you can't name it, you haven't looked.
5. **The flip question is answered:** *"What single fact, if true, would reverse this call?"* — then
   check whether that fact is already true. (Maia 300 was exactly this and it was already true.)

### B. Quant sufficiency

6. **The full engine suite ran on current data** — `indicators.py`, `flow_anomaly.py`, and (for any
   coiling/level-testing name) `forecast.py` — not a subset chosen by convenience.
7. **All signals are reported, including the ones that disagree.** If OBV says accumulate and
   flow_pressure says distribute, the conflict is *stated*, not resolved by omission. A quant
   section with no tension in it is a red flag, not a clean read.
8. **A base rate is cited** (historical analogs), with the **drift-inflation caveat** applied to any
   Monte-Carlo number that inherits a parabolic year. The sober number leads; the flattering number
   is footnoted.
9. **The action is anchored** — a level (with touches/strength) or a dated event, plus RR. "Feels
   extended" and "looks weak" don't gate-check.

### C. Verification proportional to stakes

10. **Mandatory adversarial verify** — a fresh agent prompted to **REFUTE each load-bearing claim**
    (verdicts: CONFIRMED / WEAKENED / REFUTED, dated sources) — before shipping any of:
    - a NEW action (entry / exit / trim / stop change) on a position ≥ 2% of the affected account;
    - any **reversal** of a prior desk call;
    - any call whose thesis rests on a **rumor-tier** (unconfirmed) fact;
    - any advisory on an account the desk cannot itself trade (the user will act manually on the
      desk's word — the bar is *higher*, not lower).
    A claim that comes back WEAKENED or REFUTED forces the recommendation to be re-derived from the
    surviving evidence only — not patched.
11. **The reviewer is not the author.** Sufficiency is judged by a pass that did not build the
    thesis (fresh subagent where available; at minimum a separate pass re-reading only the evidence,
    not the conclusion).

### D. Ship / no-ship

- **All items pass** → ship, and the report states in one line that the gate ran and what the
  verification verdicts were.
- **Any item fails** → no action ships. Either do the missing work now, or deliver as
  "preliminary — not actionable" with the named gaps and a date by which the desk will close them.
- **Log it**: when the gate catches something (a flipped call, a killed rec), journal it via
  `track_record.py` with the lesson — the gate's catches are the desk's cheapest education.

---

## Placement in the flow

- **Full desk run:** the CIO gate (Step 8) asks the sufficiency question on every survivor —
  it now fails ideas for *insufficient work*, not just insufficient edge.
- **Ad-hoc advisory:** the gate runs before the reply is sent. If time pressure is real, the answer
  ships in two layers: "what I can say now (preliminary)" + "what the gate still requires."
- **The user's challenge is a tripwire:** any user pushback of the "are you sure?" form triggers a
  full re-run of this checklist plus C.10 verification — treat it as a gate failure that already
  escaped, and journal the miss.
