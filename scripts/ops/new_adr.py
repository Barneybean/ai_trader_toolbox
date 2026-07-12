#!/usr/bin/env python3
"""Scaffold a new Architecture Decision Record in docs/adr/.

    python3 scripts/ops/new_adr.py "Use long-polling instead of webhooks"

Creates the next-numbered docs/adr/NNNN-slug.md from the template and adds
an index line to docs/adr/README.md. Fill in Context / Decision /
Consequences, then commit — the ADR trail is the desk's decision memory.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path
import os
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_SCRIPTS, d) for d in ("lib", "analysis", "ops")]

DESK_DIR = Path(__file__).resolve().parent.parent.parent
ADR_DIR = DESK_DIR / "docs" / "adr"
TEMPLATE = ADR_DIR / "template.md"
INDEX = ADR_DIR / "README.md"
INDEX_MARK = "<!-- adr-index -->"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "untitled"


def next_number() -> int:
    nums = [int(m.group(1)) for p in ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md")
            if (m := re.match(r"(\d{4})-", p.name))]
    return max(nums, default=0) + 1


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) >= 2 else 2
    title = " ".join(sys.argv[1:]).strip()
    ADR_DIR.mkdir(parents=True, exist_ok=True)

    n = next_number()
    name = f"{n:04d}-{slugify(title)}.md"
    target = ADR_DIR / name
    today = dt.date.today().isoformat()

    body = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else (
        "# {number} — {title}\n\nDate: {date} · Status: Proposed\n\n"
        "## Context\n\n## Decision\n\n## Consequences\n\n## Alternatives considered\n"
    )
    target.write_text(
        body.replace("{number}", f"{n:04d}").replace("{title}", title).replace("{date}", today),
        encoding="utf-8",
    )

    if INDEX.exists() and INDEX_MARK in INDEX.read_text(encoding="utf-8"):
        text = INDEX.read_text(encoding="utf-8")
        line = f"- [{n:04d} — {title}]({name}) · {today}\n"
        INDEX.write_text(text.replace(INDEX_MARK, line + INDEX_MARK), encoding="utf-8")

    print(target)
    return 0


if __name__ == "__main__":
    import desk_log
    raise SystemExit(desk_log.run(main))
