#!/bin/zsh
set -euo pipefail

label="com.example.chat-bot-bridge"
domain="gui/$(id -u)"
bridge_dir="${0:A:h}"
source_plist="$bridge_dir/$label.plist"
installed_plist="$HOME/Library/LaunchAgents/$label.plist"
action="${1:-status}"

if [[ "$action" == "install" || "$action" == "restart" ]]; then
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
    [[ -f "$installed_plist" ]] || cp "$source_plist" "$installed_plist"
    plutil -lint "$installed_plist" >/dev/null
    launchctl bootout "$domain/$label" 2>/dev/null || true
    launchctl bootstrap "$domain" "$installed_plist"
    launchctl enable "$domain/$label"
    launchctl kickstart -k "$domain/$label"
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
    echo "usage: $0 {install|restart|status|uninstall}" >&2
    exit 2
    ;;
esac

launchctl print "$domain/$label" >/dev/null
echo "bridge service $action succeeded"
