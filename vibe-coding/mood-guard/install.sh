#!/bin/bash
# Installs MoodGuard as a desktop widget + menu-bar app that starts at login.
# Run this from Terminal: bash install.sh
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_DEST="$HOME/Library/LaunchAgents/com.yidanxu.moodguard.plist"

echo "Installing MoodGuard from $DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found — install it first (macOS ships it by default; if missing, get it from python.org)." >&2
  exit 1
fi

# Resolve the *exact* python3 binary this shell uses, and install pyobjc
# into that same one — if a different python3 launches the app later
# (e.g. a conda "base" environment vs. the system python), it won't be
# able to see the package and will silently fail to start.
PYTHON_BIN="$(command -v python3)"
echo "Using $PYTHON_BIN"

"$PYTHON_BIN" -m pip install --user --upgrade pyobjc-framework-Cocoa

if ! "$PYTHON_BIN" -c "import AppKit" >/dev/null 2>&1; then
  echo "pyobjc installed, but $PYTHON_BIN still can't import AppKit." >&2
  echo "Try running this script with a plain Terminal python3 instead of a conda/virtualenv one," >&2
  echo "e.g. run: conda deactivate   (then re-run bash install.sh)" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|__SCRIPT_PATH__|$DIR/mood_guard.py|g" -e "s|__PYTHON_PATH__|$PYTHON_BIN|g" "$DIR/com.yidanxu.moodguard.plist" > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo ""
echo "Done. MoodGuard should now show a glass widget near the top-right of your desktop,"
echo "plus an icon in the menu bar. Drag the widget anywhere; it remembers its spot."
echo "It will keep launching automatically every time you log in."
echo "If you don't see it within a few seconds, check /tmp/moodguard.err.log for errors."
