# Weekly Retrospective — the desk reads its own reports before it reads the market

Once a week (the **first desk run of the week**, or Friday after the close), the desk turns
its archive into input: every past report re-read for continuity, every logged call scored
against what actually happened, and every repeated miss converted into a toolkit calibration.
The engine is `scripts/journal/weekly_review.py`; this file is the protocol for what the desk *does*
with its output. A past report is not a record — it's an open position in the desk's judgment.

## Step 1 — Assemble the pack

```bash
python3 scripts/journal/weekly_review.py            # human pack (--json for the machine pack)
```

It returns: the **OPEN BOOK** (every open decision marked to market, with alpha vs SPY and
STOP-BREACHED/MATURED flags + pre-filled score commands), the **INSIGHTS** table (per-method
hit-rates + live marks via `score_insights.py --mark`), the **LEVELS** sweep, and the
**ARCHIVE** re-read list (default: last 4 weeks across current `reports/*.html` and `reports/archive/YYYY-Www/*.html`).

## Step 2 — Continuity pass (re-read the archive)

Re-read every archive report in the window — *not* skimming the calls table, but the catalyst
maps, two-horizon clocks, and invalidation conditions, because those don't expire when the
file scrolls out of context. Build the **continuity board** for the new week's report:

| Call (report, date) | Then | Now | Verdict |
|---|---|---|---|
| e.g. "SYM: wait for confirmation above the trigger" (example) | example price | … | ON-TRACK / AHEAD / BROKEN / EXPIRED / SUPERSEDED |

Rules of the pass:
- **Every surfaced call from the window appears once** — including passes, vetoes, and
  watches. A WATCH that ran without us is data (the gate may be too tight), exactly like a
  BUY that broke (too loose).
- **Catalyst postmortem:** every dated event that occurred this week gets its predicted
  direction-if-hit compared to what printed. Catalyst maps are predictions; grade them.
- **Clocks:** any two-horizon call whose short-run window lapsed gets closed out loud
  (right/wrong/unresolved), not silently re-dated.
- Contradictions between an old report and current data are surfaced, never papered over —
  "the prior thesis said X; the tape has since done Y; the thesis survives/breaks because Z."

## Step 3 — Scoring pass (the numbers)

- Run every pre-filled `track_record.py score` command from the pack (matured / stopped /
  target-hit calls), then `track_record.py reflect` **one lesson per scored call** — a
  lesson names the *method*, not the outcome ("chip-wash read ignored ownership gate," not
  "SYM went down").
- `score_insights.py` per-method table goes **in the weekly report** ("desk hit-rates to
  date") — misses included. Honest reporting is the product.
- Mark the account scoreboard: week's P&L, vs SPY, per-sleeve.

## Step 4 — Calibration pass (the toolkit learns)

The point of keeping score is that the *machine* improves, not just the picks:

- **Attribute every miss** to one of: (a) input error — the desk underwrote bad numbers
  (fix: evidence-trail discipline, not the tool); (b) rule error — a gate/threshold/tell
  fired wrong or stayed silent; (c) variance — the read was sound, the coin landed tails.
  Only (b) touches the toolkit.
- **The ≥2 rule (anti-overfit):** no threshold, gate, or tell changes on one observation.
  Two independent same-mode failures = propose the edit; state it as a falsifiable
  hypothesis *before* changing the file (insight-registry rule #4 applies to the desk
  itself). One observation = log it in `journal/reflections.md` and wait.
- **Both error directions count:** gates that let a loser through AND gates that blocked a
  winner (WAIT-KNIFE names that based and ran, exit-radar TRIMs that kept running). The
  scorer can't see foregone wins unless the retrospective looks.
- **Apply and commit:** a calibration that clears the bar edits the skill/script in the same
  session, with the evidence cited in the commit message. The toolkit's git history *is*
  its learning record.
- **Method budget:** after ~30 scored insights, methods with persistent sub-coin-flip hit
  rates lose report space and sizing weight (`insight-registry.md` scoring); methods that
  hit earn it. Attention is the desk's scarcest capital.

## Step 5 — Feed the new week

The weekly run's report leads with a **"The week reviewed"** section before any new call:
scoreboard KPIs (week P&L, vs SPY, calls scored, hit rate) · the continuity board · one-line
calibration notes ("changed X because Y happened twice; watching Z"). New analysis follows —
now anchored to what the desk already said, so drift between reports becomes visible instead
of silent.

## Deliverable — a built report, by default

**Every weekly-review request produces the full bilingual HTML report** — whether it comes
inside a scheduled desk run, as an ad-hoc "run the weekly review" in a terminal, or as a
message through the chat-bot-bridge. Scaffold with `scripts/report/new_report.py`, build with
`scripts/report/build_report.py`, commit per repo convention; over the bridge, attach the built
HTML (`FILE:` directive) with the headline scoreboard in the text reply. A chat-only summary
is the exception, not the default — only when the user explicitly asks for a quick verbal
answer ("just tell me", "no report").

## Guardrails

- **Retrospective ≠ regret trading.** The output is lessons and calibrations, never revenge
  entries ("it ran without us" is a gate observation, not a chase signal).
- **Don't re-litigate scored calls** — a call scored and reflected is closed; the lesson
  carries forward, the position doesn't.
- **Survivorship honesty:** the continuity board includes the calls that died. A board of
  only winners means the pass was done wrong.
- Cross-links: per-name memory loop in `reflection-memory.md` (RECALL at Step 1 of every
  run); per-method scoring in `insight-registry.md`; this file is the weekly, whole-book
  version of both.
