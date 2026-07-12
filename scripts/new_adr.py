#!/usr/bin/env python3
"""Scaffold an Architecture Decision Record in docs/adr/ (see docs/adr/README.md).

Usage:
    python3 scripts/new_adr.py "Short decision title"     # → docs/adr/NNNN-short-decision-title.md
    python3 scripts/new_adr.py --list                      # index: number, status, title

Numbers are sequential and never reused. New ADRs start as Proposed; flip to Accepted when
the change ships, Superseded-by when a later ADR replaces it. Pure stdlib.
"""
import argparse
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADR_DIR = os.path.join(ROOT, "docs", "adr")
TEMPLATE = os.path.join(ADR_DIR, "template.md")


def _existing():
    """[(number, filename)] for every NNNN-*.md in docs/adr, sorted."""
    out = []
    for f in sorted(os.listdir(ADR_DIR)):
        m = re.match(r"^(\d{4})-.+\.md$", f)
        if m:
            out.append((int(m.group(1)), f))
    return out


def _field(path, pattern, default=""):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.search(pattern, line)
            if m:
                return m.group(1).strip()
    return default


def cmd_list():
    rows = _existing()
    if not rows:
        print("(no ADRs yet — scaffold one with: python3 scripts/new_adr.py \"Title\")")
        return 0
    for num, fname in rows:
        path = os.path.join(ADR_DIR, fname)
        title = _field(path, r"^#\s*ADR-\d{4}:\s*(.+)$", fname)
        status = _field(path, r"\*\*Status:\*\*\s*([^<]+)", "?")
        print(f"ADR-{num:04d}  {status:<22} {title}")
    return 0


def cmd_new(title, status):
    if not os.path.exists(TEMPLATE):
        print(f"new_adr: template missing at {TEMPLATE}", file=sys.stderr)
        return 1
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", title.lower())).strip("-")[:60]
    if not slug:
        print("new_adr: title produced an empty slug", file=sys.stderr)
        return 2
    num = max((n for n, _ in _existing()), default=0) + 1
    path = os.path.join(ADR_DIR, f"{num:04d}-{slug}.md")
    if os.path.exists(path):
        print(f"new_adr: {path} already exists", file=sys.stderr)
        return 1
    with open(TEMPLATE, encoding="utf-8") as f:
        body = f.read()
    body = (body.replace("{NUMBER}", f"{num:04d}")
                .replace("{TITLE}", title)
                .replace("{DATE}", date.today().isoformat())
                .replace("{STATUS}", status))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(path)
    print("Fill in Context/Decision/Consequences/Alternatives, add it to the index in "
          "docs/adr/README.md, and flip Status to Accepted when the change ships.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Scaffold an ADR in docs/adr/")
    ap.add_argument("title", nargs="?", help="short decision title")
    ap.add_argument("--status", default="Proposed",
                    help="initial status (default: Proposed)")
    ap.add_argument("--list", action="store_true", help="print the ADR index")
    args = ap.parse_args()
    if args.list:
        sys.exit(cmd_list())
    if not args.title:
        ap.error("give a title, or --list")
    sys.exit(cmd_new(args.title, args.status))


if __name__ == "__main__":
    main()
