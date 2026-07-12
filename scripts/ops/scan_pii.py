#!/usr/bin/env python3
"""Pre-publish guard for public branches — blocks PII *and* personal knowledge.

Two things must not reach a public branch:
  • PII / secrets — account numbers, connector/watchlist UUIDs, API keys, private keys, emails.
    NEVER allowed public. Move them into config.local.toml / .env (git-ignored).
  • Personal knowledge — your private edge (mentor names, private theses, playbook content).
    Blocked by default. You can DELIBERATELY share by overriding (see --allow-knowledge).

Exits non-zero on any blocking match, so it can gate a commit/push (git hooks) or CI.

    python3 scripts/ops/scan_pii.py                    # scan tracked files (default)
    python3 scripts/ops/scan_pii.py --all              # whole working tree (respects .gitignore)
    python3 scripts/ops/scan_pii.py --staged           # only staged files (pre-commit)
    python3 scripts/ops/scan_pii.py --allow-knowledge  # skip the personal-knowledge list (PII still blocks)
    python3 scripts/ops/scan_pii.py --accounts-only    # tier-0: account identifiers ONLY — enforced on
                                                   # EVERY branch (incl. private). Account numbers,
                                                   # holder names, and connector ids must be masked
                                                   # (last-4, e.g. the configured account) in ANY committed file.

Denylists (one term per line, '#' comments), loaded if present:
  scripts/ops/pii_denylist.txt / .local.txt        — exact secret strings (account #s). Always block.
  scripts/ops/knowledge_denylist.txt / .local.txt  — personal-knowledge markers. Block unless --allow-knowledge.
The *.local.txt files are git-ignored, so your real terms are never committed.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (label, regex, hard?)  hard=True → failure; hard=False → warning only.  These are PII/secrets.
PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), True),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), True),
    # Legacy keys are a single long token; newer keys have a known structured
    # prefix.  A broad `[A-Za-z0-9_-]+` pattern misclassifies URL slugs such as
    # `sk-hynix-oil-prices-chip-stocks` as credentials.
    ("OpenAI-style key", re.compile(
        r"\b(?:sk-[A-Za-z0-9]{20,}|sk-(?:proj|svcacct)-[A-Za-z0-9_-]{20,})\b"), True),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), True),
    ("generic secret assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"), True),
    ("account_number with value", re.compile(r"(?i)account[_ ]?number\D{0,4}\d{6,}"), True),
    ("masked account fragment (\u2022\u2022\u2022\u20224digits)", re.compile(r"[\u2022]{2,}\s*\d{4}"), True),
    ("broker applink w/ account", re.compile(r"applink\.[a-z]+\.com/\S*account_number=\d+"), True),
    ("UUID (watchlist/connector id)", re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), True),
    ("bare 8-10 digit number (acct?)", re.compile(r"(?<!\d)\d{8,10}(?!\d)"), False),
    ("email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), False),
]

# Substrings that are OK even if a pattern matches them.
ALLOW = ["noreply@", "example.com", "user@", "YOUR_", "xxxxxxxx-xxxx", "your-watchlist-uuid",
         "1SVswX2V_vE", "••••1234"]

SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".svg", ".lock", ".pyc"}


def tracked_files(mode):
    if mode == "all":
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    elif mode == "staged":
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    else:
        cmd = ["git", "ls-files"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.strip()
        if p and os.path.splitext(p)[1].lower() not in SKIP_EXT:
            full = os.path.join(ROOT, p)
            if os.path.isfile(full):
                yield p, full


def _load(base):
    """Load a denylist: committed <base>.txt + git-ignored <base>.local.txt."""
    terms = []
    paths = [
        os.path.join(ROOT, "scripts", "ops", base + ".txt"),
        os.path.join(ROOT, "scripts", "ops", base + ".local.txt"),
    ]
    # Read the former root-level local PII file for one-way migration compatibility.
    # New installations and documentation use scripts/ops/pii_denylist.local.txt.
    if base == "pii_denylist":
        paths.append(os.path.join(ROOT, "scripts", "pii_denylist.local.txt"))
    for path in paths:
        if os.path.exists(path):
            for line in open(path):
                line = line.split("#", 1)[0].strip()
                if line:
                    terms.append(line)
    return sorted(set(terms))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_const", dest="mode", const="all")
    g.add_argument("--staged", action="store_const", dest="mode", const="staged")
    ap.add_argument("--allow-knowledge", action="store_true",
                    help="deliberately allow personal-knowledge terms (PII/secrets still block)")
    ap.add_argument("--accounts-only", action="store_true",
                    help="tier-0 scan: account identifiers only; for EVERY branch incl. private")
    ap.set_defaults(mode="tracked")
    args = ap.parse_args()

    pii_terms = _load("pii_denylist")
    know_terms = [] if args.allow_knowledge else _load("knowledge_denylist")

    # Tier-0 (--accounts-only): account identifiers are blocked on EVERY branch, private
    # included — committed artifacts must use masked forms (last-4). Restrict the scan to
    # the account-shaped patterns + the denylist; knowledge rules don't apply here.
    if args.accounts_only:
        tier0 = {"account_number with value", "broker applink w/ account"}
        patterns = [(l, rx, h) for l, rx, h in PATTERNS if l in tier0]
        know_terms = []
    else:
        patterns = PATTERNS

    hard, warn = [], []   # (rel, line, label, snippet, kind)  kind: pii | knowledge | pattern
    for rel, full in tracked_files(args.mode):
        try:
            text = open(full, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for term in pii_terms:
                if term in line:
                    hard.append((rel, i, f"denylisted secret '{term}'", line.strip()[:100], "pii"))
            for term in know_terms:
                if term in line:
                    hard.append((rel, i, f"personal-knowledge '{term}'", line.strip()[:100], "knowledge"))
            for label, rx, is_hard in patterns:
                m = rx.search(line)
                # ALLOW is judged against the matched span (+ a little context),
                # not the whole line — a docs URL on the same line must not
                # shadow a genuine secret next to it.
                if m and not any(a in line[max(0, m.start() - 20):m.end() + 20] for a in ALLOW):
                    (hard if is_hard else warn).append((rel, i, label, line.strip()[:100], "pattern"))

    def show(rows, tag):
        for rel, i, label, snip, _kind in rows:
            print(f"  {tag} {rel}:{i}  [{label}]  {snip}")

    if warn:
        print(f"\n⚠️  {len(warn)} warning(s) — review (may be false positives):")
        show(warn, "warn")
    if hard:
        print(f"\n❌ {len(hard)} BLOCKING match(es) — must not reach a public branch:")
        show(hard, "FAIL")
        if args.accounts_only:
            print("\n  • Account identifier in a committed file — mask it to last-4 (e.g. the configured account)")
            print("    or move it into config.local.toml (git-ignored). Applies on EVERY branch.")
        elif any(h[4] in ("pii", "pattern") for h in hard):
            print("\n  • PII/secret → move it into config.local.toml / .env (git-ignored). Never publish.")
        if any(h[4] == "knowledge" for h in hard):
            print("\n  • Personal knowledge → keep it on your private branch. To DELIBERATELY share it,")
            print("    re-run with an explicit override:  ALLOW_PERSONAL=1 git commit/push …")
        sys.exit(1)
    print(f"\n✅ scan_pii: clean ({args.mode} files"
          + (f", {len(warn)} warning(s)" if warn else "")
          + (", personal-knowledge check SKIPPED" if args.allow_knowledge else "") + ").")


if __name__ == "__main__":
    main()
