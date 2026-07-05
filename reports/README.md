# Reports

Dated archive of AI Trader runs. Each run is delivered — and **committed** — as
**styled, self-contained HTML** (`.html`), with per-name charts under `charts/`.

The markdown (`.md`) is only a **local build intermediate**: `new_report.py` scaffolds it,
the run fills it, `build_report.py` renders it to HTML — then it is **not kept in the repo**
(the HTML is the artifact). Regenerate a `.md` locally only if you need to edit and re-render.

## Naming

`report_<YYYY-MM-DD>_<title>_<model>.html` — the committed deliverable (SVG charts inlined, so
it's one portable file). **This is what you open/share.**
- **date** — run date (Pacific), ISO so files sort chronologically.
- **title** — the run's focus, slugified: `daily-desk-run`, `nvda-deep-dive`, `watchlist-review`.
- **model** — the AI model that ran the desk, slugified: `claude-fable-5`, `gpt-5`, …

Example: `report_2026-07-05_daily-desk-run_claude-fable-5.html`
`charts/<TICKER>-YYYY-MM-DD-{price,chips,gauges}.svg` — the per-name chart sources.

## How they're produced

The daily report is a **full desk run** of AI Trader, executed
in an interactive session so the Robinhood connector (live positions, quotes,
watchlists) is available. It is **not** an unattended cloud job — a cloud agent
can't write to this local folder, and a headless local run loses the Robinhood
connector.

### One-command trigger

In a session with the desk skill and Robinhood connected, say:

> run the daily desk report

That runs the full pipeline and saves the result here. The three build steps:

```bash
# 1) dated markdown scaffold (title + section skeleton) — fill it with the analysis
python3 scripts/new_report.py --market open --date 2026-07-03 \
    --title daily-desk-run --model claude-fable-5

# 2) per-name charts (reuses the historicals already pulled for indicators.py)
python3 scripts/charts.py <historicals.json> --symbol SOFI --price <live> --float <float> \
    --out reports/charts --date 2026-07-03
#    → paste the printed image-embed block into that name's block in the .md

# 3) render the styled, self-contained HTML deliverable (charts inlined)
python3 scripts/build_report.py reports/report_2026-07-03_daily-desk-run_claude-fable-5.md
```

`new_report.py` builds only the scaffold; the analysis is filled by the desk run.
`charts.py` and `build_report.py` are documented in `skills/execution/data-and-execution.md`.

## Publishing

Each report is committed and pushed to your GitHub repo so
there's a versioned history — commit the **`.html` and `charts/`** (the `.md` is a local
build intermediate and is not committed):

```bash
git add reports/*.html reports/charts && git commit -m "Daily desk report YYYY-MM-DD" && git push
```

