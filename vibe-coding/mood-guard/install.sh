#!/bin/bash
# Installs MoodGuard as a menu-bar app that starts automatically at login.
# Run this from Terminal: bash install.sh
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_DEST="$HOME/Library/LaunchAgents/com.yidanxu.moodguard.plist"

echo "Installing MoodGuard from $DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found — install it first (macOS ships it by default; if missing, get it from python.org)." >&2
  exit 1
fi

python3 -m pip install --user --upgrade rumps

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__SCRIPT_PATH__|$DIR/mood_guard.py|g" "$DIR/com.yidanxu.moodguard.plist" > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo ""
echo "Done. MoodGuard should now show an icon in your menu bar (top-right of the screen)."
echo "It will keep launching automatically every time you log in."
echo "If you don't see it within a few seconds, check /tmp/moodguard.err.log for errors."
