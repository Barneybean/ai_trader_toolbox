#!/usr/bin/env python3
"""Keep only the current ISO week's finished reports in ``reports/``.

Reports from every other week live in ``reports/archive/YYYY-Www/``.  The date
comes from the canonical ``report_YYYY-MM-DD_...html`` filename, not mtime, so
copying or rebuilding a report cannot put it in the wrong week.
"""
import argparse
import datetime as dt
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS = os.path.join(ROOT, "reports")
ARCHIVE = os.path.join(REPORTS, "archive")
CHARTS = os.path.join(REPORTS, "assets", "charts")
MARKET_DATA = os.path.join(REPORTS, "cache", "market-data")
BUILD = os.path.join(REPORTS, ".build")
REPORT_RE = re.compile(r"^report_(\d{4}-\d{2}-\d{2})_.+\.html$")


def week_name(day):
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def organize_reports(today=None):
    """Move non-current root reports into weekly archive folders.

    Returns a mapping of absolute old paths to absolute new paths.
    """
    today = today or dt.date.today()
    current_week = week_name(today)
    moved = {}
    os.makedirs(ARCHIVE, exist_ok=True)
    for name in sorted(os.listdir(REPORTS)):
        src = os.path.join(REPORTS, name)
        if not os.path.isfile(src):
            continue
        match = REPORT_RE.match(name)
        if not match:
            continue
        report_day = dt.date.fromisoformat(match.group(1))
        report_week = week_name(report_day)
        if report_week == current_week:
            continue
        folder = os.path.join(ARCHIVE, report_week)
        os.makedirs(folder, exist_ok=True)
        dst = os.path.join(folder, name)
        # Rebuilding an old report intentionally refreshes its archived copy.
        # os.replace is atomic on this filesystem and avoids duplicate root files.
        if os.path.exists(dst):
            os.replace(src, dst)
        else:
            shutil.move(src, dst)
        moved[os.path.abspath(src)] = os.path.abspath(dst)
    return moved


def organize_support_files():
    """Migrate legacy flat chart, data, and build directories by ISO week."""
    rules = (
        (os.path.join(REPORTS, "charts"), CHARTS, re.compile(r"^[A-Z0-9.^=-]+-(\d{4}-\d{2}-\d{2})-.+\.svg$")),
        (os.path.join(REPORTS, "data"), MARKET_DATA, re.compile(r"^.+-(\d{4}-\d{2}-\d{2})\.json$")),
        (BUILD, BUILD, re.compile(r"^report_(\d{4}-\d{2}-\d{2})_.+\.md$")),
    )
    moved = {}
    for source, target_root, pattern in rules:
        if not os.path.isdir(source):
            continue
        for name in sorted(os.listdir(source)):
            src = os.path.join(source, name)
            if not os.path.isfile(src):
                continue
            match = pattern.match(name)
            if not match:
                continue
            folder = os.path.join(target_root, week_name(dt.date.fromisoformat(match.group(1))))
            os.makedirs(folder, exist_ok=True)
            dst = os.path.join(folder, name)
            os.replace(src, dst)
            moved[os.path.abspath(src)] = os.path.abspath(dst)
    return moved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", help="override current date for testing (YYYY-MM-DD)")
    args = parser.parse_args(argv)
    today = dt.date.fromisoformat(args.today) if args.today else None
    moved = organize_reports(today)
    moved.update(organize_support_files())
    for old, new in moved.items():
        print(f"{os.path.relpath(old, ROOT)} -> {os.path.relpath(new, ROOT)}")
    print(f"Current week: {week_name(today or dt.date.today())}; organized {len(moved)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
