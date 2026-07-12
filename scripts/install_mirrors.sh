#!/usr/bin/env bash
# Compatibility launcher; canonical implementation: scripts/ops/install_mirrors.sh.
set -euo pipefail
exec "$(dirname "$0")/ops/install_mirrors.sh" "$@"
