# MoodGuard

A menu-bar app for one specific pattern: working alone at home for days at a
stretch, skipping food, sleep and people, and ending up irritable without
knowing why until it's already happened.

MoodGuard tracks seven things that reliably recharge you:

1. Seeing my boyfriend for 3+ hours
2. Long time with a cat or dog
3. A real meal out at a restaurant
4. Travel
5. Meeting new people, talking a lot
6. A big win at work
7. Swimming

Check one off the moment it happens. If 14 days pass with none of them
checked, MoodGuard sends a macOS notification — the idea is to catch the
drift *before* the low mood arrives, not explain it afterwards. The menu-bar
icon also quietly shifts (🙂 → 😐 → ⚠️ → 🚨) as the 14-day window closes in,
so the warning is visible at a glance even before it fires.

## Install (on your Mac, not this session)

```
cd mood-guard
bash install.sh
```

This installs the `rumps` Python package, and registers MoodGuard to launch
automatically every time you log in (via a LaunchAgent) — you won't need to
open it manually again.

## Uninstall

```
bash uninstall.sh
```

## How it works

- `mood_guard.py` — the menu-bar app itself, built with [rumps](https://github.com/jaredks/rumps).
  Each activity is a native checkbox menu item; checking it logs today's
  date. A background timer checks hourly whether 14 days have passed since
  *any* activity was last logged, and fires a notification via `osascript`
  (more reliable than rumps' own notification API on modern macOS, which
  requires a signed .app bundle to work consistently).
- Data lives at `~/Library/Application Support/MoodGuard/data.json` — a
  simple log of dates per activity, so nothing is lost between restarts.
- `com.yidanxu.moodguard.plist` + `install.sh` — a standard macOS
  LaunchAgent, the normal way small utilities auto-start at login without
  needing to be a full packaged .app.

## A note on testing

This was built and logic-tested (date math, the 14-day threshold, data
persistence, notification-string escaping) outside of macOS, since it was
written in a Linux sandbox — `rumps` itself only runs on macOS, so the menu
bar UI, the LaunchAgent, and native notifications haven't been run
end-to-end yet. Run `install.sh` and give it a try; if anything doesn't
behave as expected, the error log is at `/tmp/moodguard.err.log`.
