#!/bin/bash
# Stops MoodGuard and removes it from login items.
# Your activity history is kept — delete
# ~/Library/Application\ Support/MoodGuard/data.json yourself if you want it gone too.
set -e

PLIST_DEST="$HOME/Library/LaunchAgents/com.yidanxu.moodguard.plist"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
rm -f "$PLIST_DEST"

echo "MoodGuard removed from login items and stopped."
echo "Your activity log is untouched at: ~/Library/Application Support/MoodGuard/data.json"
