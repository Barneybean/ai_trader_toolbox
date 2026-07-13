#!/bin/zsh
set -euo pipefail

label="com.example.chat-bot-bridge"
domain="gui/$(id -u)"
bridge_dir="${0:A:h}"
source_plist="$bridge_dir/$label.plist"
installed_plist="$HOME/Library/LaunchAgents/$label.plist"
restart_request="${BRIDGE_RESTART_REQUEST_FILE:-$bridge_dir/logs/restart-request.json}"
action="${1:-status}"

if [[ "$action" == "install" || "$action" == "restart" || "$action" == "activate" ]]; then
  if grep -q 'YOUR_NAME' "$source_plist"; then
    echo "edit YOUR_NAME and executable paths in $source_plist before installing" >&2
    exit 2
  fi
fi

case "$action" in
  install)
    mkdir -p "$HOME/Library/LaunchAgents"
    cp "$source_plist" "$installed_plist"
    plutil -lint "$installed_plist" >/dev/null
    launchctl bootout "$domain/$label" 2>/dev/null || true
    launchctl bootstrap "$domain" "$installed_plist"
    launchctl enable "$domain/$label"
    launchctl kickstart -k "$domain/$label"
    ;;
  restart)
    if [[ "${BRIDGE_MANAGED_RUN:-0}" == "1" ]]; then
      mkdir -p "$(dirname "$restart_request")"
      tmp="$restart_request.tmp.$$"
      printf '{"requested_at":"%s","reason":"agent requested bridge activation"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$tmp"
      mv "$tmp" "$restart_request"
      echo "bridge activation deferred until the current phone run replies"
      exit 0
    fi
    "$0" activate
    exit 0
    ;;
  activate)
    # This path is safe from a terminal or detached helper. kickstart keeps the
    # launchd registration intact; bootstrap recovers an absent service.
    sleep "${BRIDGE_RESTART_DELAY_S:-0}"
    [[ -f "$installed_plist" ]] || cp "$source_plist" "$installed_plist"
    plutil -lint "$installed_plist" >/dev/null
    launchctl enable "$domain/$label"
    if launchctl print "$domain/$label" >/dev/null 2>&1; then
      launchctl kickstart -k "$domain/$label"
    else
      launchctl bootstrap "$domain" "$installed_plist"
    fi
    ;;
  uninstall)
    launchctl bootout "$domain/$label" 2>/dev/null || true
    rm -f "$installed_plist"
    echo "bridge service removed"
    exit 0
    ;;
  status)
    launchctl print "$domain/$label"
    exit 0
    ;;
  *)
    echo "usage: $0 {install|restart|activate|status|uninstall}" >&2
    exit 2
    ;;
esac

launchctl print "$domain/$label" >/dev/null
echo "bridge service $action succeeded"
