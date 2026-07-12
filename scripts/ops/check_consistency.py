#!/usr/bin/env python3
"""Consistency gate — mechanical checks that a change doesn't conflict with the toolkit.

Runs locally and in public CI. The toolkit's docs are agent context, so they must stay dense,
registered, non-contradictory, and aligned with canonical public paths.

ERRORS (exit 1 — fix before pushing):
  - broken internal markdown links (references to renamed/removed/never-added files)
  - ADR integrity: duplicate numbers, "Superseded by NNNN" pointing nowhere, an ADR
    missing from the docs/adr/README.md index, template placeholders left unfilled
  - unregistered sector playbooks (a sectors/*.md absent from sector-playbooks.md)
  - filenames that collide case-insensitively
  - obsolete parallel feature directories that conflict with the boundary standard

WARNINGS (exit 0 — judgment call):
  - condensed-wording budgets: skills/*.md over ~2,600 words, SKILL.md over ~5,800
    (agent-context files cost tokens on every desk run — condense, don't split)
  - a top-level protocol in skills/ absent from both canonical routing maps
  - a script in scripts/ that no doc mentions

Semantic conflicts—contradicting an accepted ADR or adding a competing mechanism—remain a human
review responsibility; see CONTRIBUTING.md.

Usage:  python3 scripts/ops/check_consistency.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import os

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import desk_log  # noqa: E402

DESK_DIR = Path(__file__).resolve().parent.parent.parent
ADR_DIR = DESK_DIR / "docs" / "adr"
SYNC_POLICY = DESK_DIR / "docs" / "source-sync-policy.json"
SECTORS_DIR = DESK_DIR / "skills" / "analysis" / "sectors"
SECTOR_REGISTRY = DESK_DIR / "skills" / "analysis" / "sector-playbooks.md"
SKILL_WORD_BUDGET = 2600      # per skills/*.md file
CHARTER_WORD_BUDGET = 5800    # SKILL.md (the charter runs bigger)
SKIP_DIRS = {".git", "__pycache__", "journal", "logs", "reports", "dist", "node_modules"}

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
SUPERSEDE_RE = re.compile(r"Superseded by (?:ADR-)?(\d{4})")
ADR_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")


def _tracked_files() -> list[str]:
    """Repo files to check — includes new, not-yet-added files so the gate works
    as a self-review before anything is staged."""
    try:
        out = subprocess.run(
            ["git", "-C", str(DESK_DIR), "ls-files", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True, text=True, check=True,
        ).stdout
        return [p for p in out.splitlines() if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = []
        for dirpath, dirnames, filenames in os.walk(DESK_DIR):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                files.append(str(Path(dirpath, f).relative_to(DESK_DIR)))
        return files


def _read(rel: str) -> str:
    return (DESK_DIR / rel).read_text(encoding="utf-8", errors="replace")


def check_links(md_files: list[str], errors: list[str]) -> None:
    for rel in md_files:
        base = (DESK_DIR / rel).parent
        for target in LINK_RE.findall(_read(rel)):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue  # external URL / mailto / same-file anchor
            if "<" in target:
                continue  # template placeholder, e.g. charts/<TICKER>-<date>.svg
            path = target.split("#", 1)[0]
            if path and not ((base / path).exists() or (DESK_DIR / path).exists()):
                errors.append(f"{rel}: broken link → {target}")


def check_adrs(errors: list[str]) -> None:
    if not ADR_DIR.is_dir():
        return
    index = (ADR_DIR / "README.md").read_text(encoding="utf-8", errors="replace") \
        if (ADR_DIR / "README.md").exists() else ""
    seen: dict[str, str] = {}
    names = [p.name for p in ADR_DIR.iterdir()]
    for fname in sorted(names):
        m = ADR_FILE_RE.match(fname)
        if not m:
            continue
        num, rel = m.group(1), f"docs/adr/{fname}"
        if num in seen:
            errors.append(f"{rel}: duplicate ADR number {num} (also {seen[num]})")
        seen[num] = fname
        body = _read(rel)
        if re.search(r"\{(NUMBER|TITLE|DATE|STATUS)\}", body):
            errors.append(f"{rel}: template placeholder left unfilled")
        for target in SUPERSEDE_RE.findall(body):
            if not any(n.startswith(target + "-") for n in names):
                errors.append(f"{rel}: supersedes {target}, which does not exist")
        if fname not in index:
            errors.append(f"{rel}: not listed in the docs/adr/README.md index")


def check_playbook_registration(errors: list[str]) -> None:
    maps = [  # (playbook dir, coverage maps every playbook must appear in)
        (SECTORS_DIR, [SECTORS_DIR / "README.md", SECTOR_REGISTRY]),
        (DESK_DIR / "skills" / "analysis" / "stocks",
         [DESK_DIR / "skills" / "analysis" / "stocks" / "README.md"]),
    ]
    for pb_dir, coverage in maps:
        if not pb_dir.is_dir():
            continue
        registries = {c: c.read_text(encoding="utf-8", errors="replace")
                      for c in coverage if c.exists()}
        for p in sorted(pb_dir.glob("*.md")):
            if p.name in ("README.md", "_TEMPLATE.md"):
                continue
            for c, text in registries.items():
                if p.name not in text:
                    errors.append(f"{p.relative_to(DESK_DIR)}: not registered in "
                                  f"{c.relative_to(DESK_DIR)}")


def check_case_collisions(files: list[str], errors: list[str]) -> None:
    lowered: dict[str, str] = {}
    for f in files:
        key = f.lower()
        if key in lowered and lowered[key] != f:
            errors.append(f"{f}: case-insensitive collision with {lowered[key]}")
        lowered[key] = f


def check_canonical_paths(errors: list[str]) -> None:
    if not SYNC_POLICY.is_file():
        errors.append("docs/source-sync-policy.json: missing canonical machine policy")
        return
    try:
        policy = json.loads(SYNC_POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"docs/source-sync-policy.json: unreadable/invalid ({exc})")
        return
    for item in policy.get("canonical_paths", []):
        canonical = item.get("path")
        if not canonical:
            errors.append("docs/source-sync-policy.json: canonical entry missing path")
            continue
        if item.get("required") and not (DESK_DIR / canonical).exists():
            errors.append(f"{canonical}: required canonical path is missing")
        for alias in item.get("aliases", []):
            if (DESK_DIR / alias).exists():
                errors.append(f"{alias}: obsolete alias; use {canonical}")


def check_word_budgets(md_files: list[str], warnings: list[str]) -> None:
    for rel in md_files:
        if rel == "SKILL.md":
            budget = CHARTER_WORD_BUDGET
        elif rel.startswith("skills/") and not rel.endswith("_TEMPLATE.md"):
            budget = SKILL_WORD_BUDGET
        else:
            continue
        words = len(_read(rel).split())
        if words > budget:
            warnings.append(f"{rel}: {words} words (budget ~{budget}) — condense; "
                            "this file is loaded into agent context")


def check_script_registration(files: list[str], warnings: list[str]) -> None:
    corpus = "\n".join(_read(f) for f in files
                       if f.endswith(".md") and not f.startswith("scripts/"))
    for f in sorted(files):
        if not (f.startswith("scripts/") and f.endswith(".py")):
            continue
        stem = Path(f).stem
        if stem not in corpus:
            warnings.append(f"{f}: no doc mentions '{stem}' — register it "
                            "(AGENTS.md, SKILL.md, scripts/README.md, or the skill it serves)")


def check_skill_registration(files: list[str], warnings: list[str]) -> None:
    """Protocols must be discoverable from SKILL.md or the annotated skills map.

    Sector/stock playbooks have their own registries and are checked separately.
    Templates and README files are infrastructure rather than runnable protocols.
    """
    maps = _read("SKILL.md") + "\n" + _read("skills/README.md")
    for f in sorted(files):
        if not (f.startswith("skills/") and f.endswith(".md")):
            continue
        p = Path(f)
        if p.name in {"README.md", "_TEMPLATE.md"}:
            continue
        if "sectors" in p.parts or "stocks" in p.parts:
            continue
        if p.name not in maps:
            warnings.append(f"{f}: protocol is absent from SKILL.md and skills/README.md "
                            "— route it or retire it")


def main() -> int:
    files = _tracked_files()
    md_files = [f for f in files if f.endswith(".md") and (DESK_DIR / f).exists()]
    errors: list[str] = []
    warnings: list[str] = []
    check_links(md_files, errors)
    check_adrs(errors)
    check_playbook_registration(errors)
    check_case_collisions(files, errors)
    check_canonical_paths(errors)
    check_word_budgets(md_files, warnings)
    check_skill_registration(files, warnings)
    check_script_registration(files, warnings)

    for w in warnings:
        print(f"  warn {w}")
    for e in errors:
        print(f"  ERR  {e}")
    desk_log.log_event("check_consistency", "gate_result",
                       level="error" if errors else "info",
                       errors=len(errors), warnings=len(warnings))
    if errors:
        print(f"\n✋ check_consistency: {len(errors)} conflict(s) — fix before committing.")
        return 1
    tail = f" ({len(warnings)} warning(s) to eyeball.)" if warnings else ""
    print(f"✅ check_consistency: no conflicts.{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(desk_log.run(main))
