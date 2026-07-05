#!/usr/bin/env bash
# Wire every agent runtime back to THIS folder — mirrors, not copies.
# Run once (and it's safe to re-run): bash scripts/install_mirrors.sh
set -euo pipefail

# Resolve the repo root from this script's location, no matter where it's called from.
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Source of truth: $SRC"
echo

# 1) Claude Code — personal skill via symlink (auto-discovered, always current).
CC_SKILLS="$HOME/.claude/skills"
mkdir -p "$CC_SKILLS"
LINK="$CC_SKILLS/ai-trader"
if [ -L "$LINK" ]; then
  ln -sfn "$SRC" "$LINK"; echo "Claude Code: refreshed symlink $LINK -> $SRC"
elif [ -e "$LINK" ]; then
  echo "Claude Code: SKIPPED — $LINK exists and is NOT a symlink. Move it aside, then re-run."
else
  ln -s "$SRC" "$LINK"; echo "Claude Code: linked $LINK -> $SRC"
fi

# 2) Codex — reads AGENTS.md from the working dir automatically when run inside the repo.
#    Also point global Codex at it so it's available from anywhere.
if [ -f "$SRC/AGENTS.md" ]; then
  echo "Codex (in-repo): AGENTS.md present — run 'codex' from $SRC and it's picked up."
  CODEX_DIR="$HOME/.codex"
  mkdir -p "$CODEX_DIR"
  GLINK="$CODEX_DIR/AGENTS.md"
  if [ -L "$GLINK" ] || [ ! -e "$GLINK" ]; then
    ln -sfn "$SRC/AGENTS.md" "$GLINK"
    echo "Codex (global): linked $GLINK -> $SRC/AGENTS.md"
  else
    echo "Codex (global): SKIPPED — $GLINK exists and is not a symlink. Merge it by hand if you want global access."
  fi
fi

# 3) Claude Desktop — needs an uploaded bundle; regenerate it from source.
echo
echo "Claude Desktop: run 'python3 scripts/package_skill.py' then upload dist/ai-trader.zip"
echo "                (Settings -> Capabilities -> Skills). Re-package after edits."
echo
echo "Done. One folder, three runtimes."

