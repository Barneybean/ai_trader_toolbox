# User Manual

How to drive the desk from your phone or a terminal. The methodology itself lives in
`SKILL.md` and `skills/`.

---

## Daily-report promise

You do not need to say “complete” to get complete work. “Run a daily report,” “run a full daily
report,” and “run a complete daily report” all invoke the maximum decision-grade pipeline: recall
history first, gather enough fresh dated evidence, run the relevant roles and engines, debate the
thesis, apply the risk and sufficiency gates, and return the full human-reviewable report.

Use “quick update,” “changes only,” or “status only” only when you want monitoring rather than a
report. If a quick check surfaces a possible action, the desk should escalate to the full analysis
before recommending anything.

---

## Talking to the desk

**Terminal:** run your coding agent in the repo and ask for a report, analysis, or review in plain
language.

**Phone:** use the optional bridge in `docs/phone-connection.md` if you want the same interaction
from a messaging app.

Examples:

- `Run a daily report on NVDA.`
- `Run a complete report on AI robotics opportunities.`
- `Analyze META.`
- `What changed since the last run?`

---

## Modes and commands

The public docs expose the same command surface as the phone bridge.

| Command | What it does |
|---|---|
| `/status` | Show bridge health, active agent, mode, and session state. |
| `/agent` | Show the current agent preference and fallback order. |
| `/agent auto` | Use the configured priority and fall back when an agent is unavailable. |
| `/agent codex` · `/agent claude` | Pin one agent and disable automatic fallback. |
| `/new` | Start fresh sessions and clear old conversation state. |
| `/mode` | Show the current trading mode. |
| `/mode manual` | Require explicit confirmation for each order. |
| `/mode semi` | Propose numbered tickets and wait for approval. |
| `/mode full` | Allow the opt-in autonomous mode, still bound by the desk gates. |
| `/help` | List the supported commands. |

---

## Safety rules

- Never publish secrets, account identifiers, or live session IDs.
- Keep the bridge and agent order configurable.
- Use the public boundary standard in `docs/open-source-boundary.md` when deciding what belongs in
  the reusable core.
- A significant docs or behavior change should run `python3 scripts/ops/smoke_test.py` and the normal
  consistency / PII checks before you ship it.
