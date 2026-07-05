#!/usr/bin/env bash
# Install the local PII gate (pre-commit + pre-push hooks). Run once per clone.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push scripts/scan_pii.py 2>/dev/null || true
echo "✅ PII gate installed (core.hooksPath=.githooks)."
echo "   • pre-commit: blocks staging PII on a public branch"
echo "   • pre-push:   blocks pushing PII on a public branch"
echo "   The server-side CI gate (.github/workflows/pii-scan.yml) is the definitive check."
echo
echo "Tip: add your exact private strings (account #s, names) to scripts/pii_denylist.local.txt"
echo "     (git-ignored) so the gate hard-blocks them too. See scripts/pii_denylist.example.txt."

