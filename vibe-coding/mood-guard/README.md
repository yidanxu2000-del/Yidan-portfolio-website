# MoodGuard

A small glass widget that floats on the Mac desktop, built for one specific
pattern: when I'm carrying an urgent, high-pressure task solo, I get fully
absorbed and lose track of everything else, food, sleep, people, for days
at a time. MoodGuard tracks the things that actually recharge me, so I
notice the drift before a low mood lands instead of after.

The widget shows a big number: days since the last recharge. Below it, your
recharge activities, fully customisable. Did one? Click it and it's checked
off for today. If 14 days pass with no real, positive recharge logged,
MoodGuard sends a macOS notification, warning you to watch for a low mood
and step in early. The menu-bar icon also quietly shifts (🙂 → 😐 → ⚠️ → 🚨)
as the window closes in.

## What's in v2

- **A floating desktop widget**, frameless dark glass, always visible.
  Drag it anywhere; it remembers its spot. Hide/show it from the menu-bar
  icon.
- **Customisable activities.** Click "✎ customise" on the widget (or the
  menu-bar icon → "Customise activities…"), edit the list, one per line,
  up to 12. History for removed lines is kept.
- Check-ins from the old menu-bar version carry over automatically.

## Install (on your Mac)

```
cd mood-guard
bash install.sh
```

This installs the `pyobjc` Cocoa bindings and registers MoodGuard to launch
automatically at login (via a LaunchAgent). You won't need to open it
manually again.

## Uninstall

```
bash uninstall.sh
```

## How it works

- `mood_guard.py` — the app, built directly on AppKit via PyObjC. The
  widget is a borderless, non-activating `NSPanel` with an
  `NSVisualEffectView` glass background, floating above the desktop on
  every Space. A background timer checks hourly whether 14 days have
  passed since *any* activity was last logged, and fires a notification
  via `osascript` (more reliable than unsigned-app notification APIs on
  modern macOS).
- Data lives at `~/Library/Application Support/MoodGuard/data.json`: the
  activity list, a log of dates per activity, and the widget's position.
- `com.yidanxu.moodguard.plist` + `install.sh` — a standard macOS
  LaunchAgent, the normal way small utilities auto-start at login.

## A note on testing

Built in a Linux sandbox, so the AppKit UI hasn't been run end-to-end
(the date math, warning threshold, data migration and activity parsing are
unit-tested). Run `install.sh` and try it; if anything misbehaves, the
error log is at `/tmp/moodguard.err.log`.

## License

MIT. See [LICENSE](LICENSE). Built by [Yidan Xu](https://yidanxu.netlify.app) with Claude Code; part of a small collection of vibe-coded tools on her [portfolio](https://yidanxu.netlify.app/#thinking).
