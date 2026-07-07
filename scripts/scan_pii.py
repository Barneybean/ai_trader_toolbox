#!/usr/bin/env python3
"""Pre-publish PII / credential guard.

Scans git-TRACKED files for things that must never reach a public repo — brokerage account
numbers, connector/watchlist UUIDs, API keys and other secrets, private-key blocks, and personal
emails. Exits non-zero if any HARD match is found, so it can gate a commit/publish (CI or a
pre-commit hook).

    python3 scripts/scan_pii.py            # scan tracked files (default)
    python3 scripts/scan_pii.py --all      # scan the whole working tree (respecting .gitignore)
    python3 scripts/scan_pii.py --staged    # scan only staged files (for a pre-commit hook)

    python3 scripts/scan_pii.py --accounts-only  # tier-0: account identifiers ONLY — account
                                                 # numbers and broker applinks must be masked
                                                 # (last-4, e.g. ••••1234) in ANY committed file.

Add project-specific strings to block in `scripts/pii_denylist.txt` (one per line, '#' comments).
Tune ALLOW if a pattern is a legitimate false positive.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label, regex, hard?)  hard=True → failure; hard=False → warning only.
PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), True),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), True),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), True),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), True),
    ("generic secret assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"), True),
    ("account_number with value", re.compile(r"(?i)account[_ ]?number\D{0,4}\d{6,}"), True),
    ("broker applink w/ account", re.compile(r"applink\.[a-z]+\.com/\S*account_number=\d+"), True),
    ("UUID (watchlist/connector id)", re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), True),
    ("bare 8-10 digit number (acct?)", re.compile(r"(?<!\d)\d{8,10}(?!\d)"), False),
    ("email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), False),
]

# Substrings that are OK even if a pattern matches them.
ALLOW = ["noreply@", "example.com", "user@", "YOUR_", "xxxxxxxx-xxxx", "your-watchlist-uuid",
         "1SVswX2V_vE"]

# Don't scan these (binary/lock/build); markdown/py/toml/txt/yml are scanned.
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


def load_denylist():
    # Committed generic terms + a git-ignored local file for exact private strings (secrets/names).
    terms = []
    for name in ("pii_denylist.txt", "pii_denylist.local.txt"):
        path = os.path.join(ROOT, "scripts", name)
        if os.path.exists(path):
            for line in open(path):
                line = line.split("#", 1)[0].strip()
                if line:
                    terms.append(line)
    return terms


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_const", dest="mode", const="all")
    g.add_argument("--staged", action="store_const", dest="mode", const="staged")
    ap.add_argument("--accounts-only", action="store_true",
                    help="tier-0 scan: account identifiers only — masked (last-4) forms required")
    ap.set_defaults(mode="tracked")
    args = ap.parse_args()

    denylist = load_denylist()

    # Tier-0 (--accounts-only): committed artifacts must use masked account forms (last-4).
    # Restrict the scan to the account-shaped patterns + the denylist.
    if args.accounts_only:
        tier0 = {"account_number with value", "broker applink w/ account"}
        patterns = [(l, rx, h) for l, rx, h in PATTERNS if l in tier0]
    else:
        patterns = PATTERNS

    hard, warn = [], []
    for rel, full in tracked_files(args.mode):
        try:
            text = open(full, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for term in denylist:
                if term in line:
                    hard.append((rel, i, f"denylisted string '{term}'", line.strip()[:100]))
            if any(a in line for a in ALLOW):
                continue
            for label, rx, is_hard in patterns:
                if rx.search(line):
                    (hard if is_hard else warn).append((rel, i, label, line.strip()[:100]))

    def show(rows, tag):
        for rel, i, label, snip in rows:
            print(f"  {tag} {rel}:{i}  [{label}]  {snip}")

    if warn:
        print(f"\n⚠️  {len(warn)} warning(s) — review (may be false positives):")
        show(warn, "warn")
    if hard:
        print(f"\n❌ {len(hard)} BLOCKING match(es) — do NOT publish until resolved:")
        show(hard, "FAIL")
        if args.accounts_only:
            print("\n  • Account identifier in a committed file — mask it to last-4 (e.g. ••••1234)")
            print("    or move it into config.local.toml (git-ignored).")
        else:
            print("\nMove the value into config.local.toml / .env (git-ignored), or add a false "
                  "positive to ALLOW in scripts/scan_pii.py.")
        sys.exit(1)
    print(f"\n✅ scan_pii: no blocking PII/credentials in {args.mode} files."
          + (f" ({len(warn)} warning(s) to eyeball.)" if warn else ""))


if __name__ == "__main__":
    main()

