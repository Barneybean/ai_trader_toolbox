# Reports

Finished, self-contained desk reports with a small and predictable lifecycle.

## Directory layout

```text
reports/
├── report_YYYY-MM-DD_<title>_<model>.html  # current ISO week only
├── archive/
│   └── YYYY-Www/                          # prior-week HTML deliverables
├── assets/
│   └── charts/YYYY-Www/                   # regenerable SVG chart sources
├── cache/
│   └── market-data/YYYY-Www/              # local input cache; git-ignored
├── examples/
│   └── sample-report.html                 # maintained, non-live example
└── .build/
    └── YYYY-Www/                          # markdown sources; git-ignored
```

The root is intentionally an inbox for the current week. `organize_reports.py`
moves older HTML and partitions support files by the ISO week encoded in their
filenames. It runs automatically from `new_report.py` and `build_report.py`.

## Artifact policy

- **HTML is the deliverable.** It contains its SVG charts and can be opened or
  shared without adjacent files.
- **Chart SVGs are sources.** They are grouped by week under `assets/charts/`.
- **Market data is cache.** It is reproducible, local, and never committed.
- **Markdown is build state.** It stays under `.build/` and is never committed.
- **Archive paths are immutable by date.** Rebuilding an old report atomically
  refreshes the copy in its original ISO-week folder.

## Naming

`report_<YYYY-MM-DD>_<title>_<model>.html`

Example: `report_2026-07-11_meta-live-review_claude-fable-5.html`.

## Build workflow

```bash
# Scaffold into reports/.build/YYYY-Www/
python3 scripts/report/new_report.py --market open --date 2026-07-11 \
  --title daily-desk-run --model claude-fable-5

# Generate chart sources into reports/assets/charts/YYYY-Www/
python3 scripts/report/charts.py <historicals.json> --symbol META \
  --price <live> --float <float> --date 2026-07-11

# Build current-week HTML into reports/; charts resolve by report week
python3 scripts/report/build_report.py \
  reports/.build/2026-W28/report_2026-07-11_daily-desk-run_claude-fable-5.md \
  --out reports/report_2026-07-11_daily-desk-run_claude-fable-5.html

# Optional explicit maintenance/audit
python3 scripts/report/organize_reports.py
```

Keep personal reports local or publish them only to a private fork. The public toolkit ignores
current reports, archives, chart assets, caches, and build intermediates; only the maintained,
sanitized file under `examples/` belongs in the open-source repository.
