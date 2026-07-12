#!/usr/bin/env bash
# Compatibility launcher; canonical implementation: scripts/ops/install_hooks.sh.
set -euo pipefail
exec "$(dirname "$0")/ops/install_hooks.sh" "$@"
