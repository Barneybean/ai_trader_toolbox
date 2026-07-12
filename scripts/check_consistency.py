#!/usr/bin/env python3
"""Consistency gate — mechanical checks that a contribution doesn't conflict with the toolkit.

The desk's docs are agent context: they must stay dense, registered, and non-contradictory.
This gate catches the mechanical half of "conflicting additions" (see docs/adr/0003):

ERRORS (exit 1 — block the merge):
  - broken internal markdown links (a reference to a file that was renamed/removed/never added)
  - ADR integrity: duplicate numbers, "Superseded by ADR-NNNN" pointing nowhere, an ADR
    missing from the docs/adr/README.md index, template placeholders left unfilled
  - unregistered playbooks: a sectors/ or stocks/ file absent from its coverage map
    (two people writing the same playbook is the conflict this catches)
  - filenames that collide case-insensitively (breaks macOS ↔ Linux checkouts)

WARNINGS (exit 0 — reviewer judgment):
  - condensed-wording budget: a skills/*.md over ~2,600 words or SKILL.md over ~5,500
    (agent-context files cost tokens on every desk run — tighten, don't pad)
  - an engine in scripts/ that no doc mentions (register it in SKILL.md's reference map)

The semantic half — "does this contradict an accepted ADR or an existing skill's method?" —
is the reviewer's job; the PR checklist points there. Pure stdlib; runs local (pre-push
hook), in CI, or by hand:  python3 scripts/check_consistency.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADR_DIR = os.path.join(ROOT, "docs", "adr")
SKILL_WORD_BUDGET = 2600      # per skills/*.md file
SKILL_MD_WORD_BUDGET = 5500   # SKILL.md itself (the charter runs bigger)
SKIP_DIRS = {".git", "__pycache__", "journal", "reports", "node_modules", ".build"}

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
SUPERSEDE_RE = re.compile(r"Superseded by ADR-(\d{4})")
ADR_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")


def _tracked_files():
    """Repo files to check — git's view when available, a filtered walk otherwise."""
    try:
        # --others --exclude-standard adds new, not-yet-added files, so the gate works as a
        # self-review before anything is staged or committed.
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "--cached", "--others",
                              "--exclude-standard"], capture_output=True,
                             text=True, check=True).stdout
        return [p for p in out.splitlines() if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                files.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
        return files


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8", errors="replace") as f:
        return f.read()


def check_links(md_files, errors):
    for rel in md_files:
        base = os.path.dirname(os.path.join(ROOT, rel))
        for target in LINK_RE.findall(_read(rel)):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue  # external URL / mailto / same-file anchor
            if "<" in target:
                continue  # template placeholder, e.g. charts/<TICKER>-<date>-price.svg
            path = target.split("#", 1)[0]
            if not path:
                continue
            if not (os.path.exists(os.path.join(base, path))
                    or os.path.exists(os.path.join(ROOT, path))):
                errors.append(f"{rel}: broken link → {target}")


def check_adrs(errors):
    if not os.path.isdir(ADR_DIR):
        return
    index = _read("docs/adr/README.md") if os.path.exists(os.path.join(ADR_DIR, "README.md")) else ""
    seen = {}
    for fname in sorted(os.listdir(ADR_DIR)):
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
            if not any(f.startswith(target + "-") for f in os.listdir(ADR_DIR)):
                errors.append(f"{rel}: supersedes ADR-{target}, which does not exist")
        if fname not in index:
            errors.append(f"{rel}: not listed in the docs/adr/README.md index")


def check_playbook_registration(errors):
    maps = [  # (playbook dir, [coverage maps it must appear in])
        ("skills/analysis/sectors", ["skills/analysis/sectors/README.md",
                                     "skills/analysis/sector-playbooks.md"]),
        ("skills/analysis/stocks", ["skills/analysis/stocks/README.md"]),
    ]
    for dirrel, coverage in maps:
        dirabs = os.path.join(ROOT, dirrel)
        if not os.path.isdir(dirabs):
            continue
        registries = {c: _read(c) for c in coverage if os.path.exists(os.path.join(ROOT, c))}
        for fname in sorted(os.listdir(dirabs)):
            if not fname.endswith(".md") or fname in ("README.md", "_TEMPLATE.md"):
                continue
            for c, text in registries.items():
                if fname not in text:
                    errors.append(f"{dirrel}/{fname}: not registered in {c}")


def check_case_collisions(files, errors):
    lowered = {}
    for f in files:
        key = f.lower()
        if key in lowered and lowered[key] != f:
            errors.append(f"{f}: case-insensitive collision with {lowered[key]}")
        lowered[key] = f


def check_word_budgets(md_files, warnings):
    for rel in md_files:
        if rel == "SKILL.md":
            budget = SKILL_MD_WORD_BUDGET
        elif rel.startswith("skills/") and not rel.endswith("_TEMPLATE.md"):
            budget = SKILL_WORD_BUDGET
        else:
            continue
        words = len(_read(rel).split())
        if words > budget:
            warnings.append(f"{rel}: {words} words (budget ~{budget}) — condense; "
                            "this file is loaded into agent context")


def check_engine_registration(files, warnings):
    corpus = "\n".join(_read(f) for f in files
                       if f.endswith(".md") and not f.startswith("scripts/"))
    for f in sorted(files):
        if not (f.startswith("scripts/") and f.endswith(".py")):
            continue
        stem = os.path.basename(f)[:-3]
        if stem not in corpus:
            warnings.append(f"{f}: no doc mentions '{stem}' — register it "
                            "(SKILL.md reference map / README / a skill)")


def main():
    files = _tracked_files()
    md_files = [f for f in files if f.endswith(".md")
                and os.path.exists(os.path.join(ROOT, f))]
    errors, warnings = [], []
    check_links(md_files, errors)
    check_adrs(errors)
    check_playbook_registration(errors)
    check_case_collisions(files, errors)
    check_word_budgets(md_files, warnings)
    check_engine_registration(files, warnings)

    for w in warnings:
        print(f"  warn {w}")
    for e in errors:
        print(f"  ERR  {e}")
    if errors:
        print(f"\n✋ check_consistency: {len(errors)} conflict(s) — fix before merging.")
        return 1
    tail = f" ({len(warnings)} warning(s) to eyeball.)" if warnings else ""
    print(f"✅ check_consistency: no conflicts in tracked files.{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
