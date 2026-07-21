#!/usr/bin/env python3
"""MoodGuard — a small glass widget that lives on the desktop.

Built for one specific pattern: getting fully absorbed in an urgent, solo
task and losing track of food, sleep and people for days at a time. Tracks
a customisable list of recharge activities. One click checks an activity
off for today. If 14 days pass with nothing checked, it fires a macOS
notification, catching the drift toward a low mood before it arrives, not
explaining it after the fact.

Runs as a floating, frameless panel (drag it anywhere; it remembers where
you left it) plus a menu-bar icon showing days since the last recharge.
"""
import json
import os
import subprocess
from datetime import date, datetime

APP_NAME = "MoodGuard"
DATA_DIR = os.path.expanduser("~/Library/Application Support/MoodGuard")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
WARNING_DAYS = 14

DEFAULT_ACTIVITIES = [
    "💛 Saw my boyfriend, 3+ hours",
    "🐾 Long time with a cat or dog",
    "🍽️ Restaurant, real food",
    "✈️ Travel",
    "🗣️ Meet new people, talk a lot",
    "🏆 Big win at work",
    "🏊 Swim",
]

MAX_ACTIVITIES = 12

# ---------------------------------------------------------------- pure logic


def load_data():
    if not os.path.exists(DATA_FILE):
        data = {}
    else:
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
        except (ValueError, OSError):
            data = {}
    data.setdefault("activities", list(DEFAULT_ACTIVITIES))
    data.setdefault("log", {})
    # legacy v1 logs were keyed by short ids; fold them into label keys so
    # old check-ins keep counting toward days-since
    legacy = {
        "date": "💛 Saw my boyfriend, 3+ hours",
        "pet": "🐾 Long time with a cat or dog",
        "food": "🍽️ Restaurant, real food",
        "travel": "✈️ Travel",
        "social": "🗣️ Meet new people, talk a lot",
        "win": "🏆 Big win at work",
        "swim": "🏊 Swim",
    }
    for old_key, label in legacy.items():
        if old_key in data["log"]:
            merged = set(data["log"].get(label, [])) | set(data["log"].pop(old_key))
            data["log"][label] = sorted(merged)
    for label in data["activities"]:
        data["log"].setdefault(label, [])
    data.setdefault("last_warned", None)
    data.setdefault("widget_pos", None)
    data.setdefault("widget_hidden", False)
    return data


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def days_since_last_activity(data):
    all_dates = [d for entries in data["log"].values() for d in entries]
    if not all_dates:
        return None
    last = max(datetime.strptime(d, "%Y-%m-%d").date() for d in all_dates)
    return (date.today() - last).days


def status_icon(days):
    if days is None:
        return "🙂"  # no history yet — nothing to warn about
    if days >= WARNING_DAYS:
        return "🚨"
    if days >= WARNING_DAYS - 3:
        return "⚠️"
    if days >= 7:
        return "😐"
    return "🙂"


def parse_activity_lines(text):
    """One activity per line; blank lines dropped, order kept, dupes dropped."""
    seen, out = set(), []
    for line in text.splitlines():
        label = line.strip()
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out[:MAX_ACTIVITIES]


def send_notification(title, subtitle, message):
    # osascript (a signed system binary) posts the notification on our
    # behalf — an unsigned python script calling the notification APIs
    # directly gets silently dropped on modern macOS
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    script = 'display notification "{}" with title "{}" subtitle "{}"'.format(
        esc(message), esc(title), esc(subtitle)
    )
    subprocess.run(["osascript", "-e", script], check=False)


# ------------------------------------------------------------------- the app

try:
    import AppKit
    import objc
    from AppKit import (
        NSApp,
        NSApplication,
        NSBackingStoreBuffered,
        NSButton,
        NSColor,
        NSFont,
        NSMakeRect,
        NSMenu,
        NSMenuItem,
        NSMutableParagraphStyle,
        NSObject,
        NSPanel,
        NSScreen,
        NSScrollView,
        NSStatusBar,
        NSTextField,
        NSTextView,
        NSVisualEffectView,
    )
    from PyObjCTools import AppHelper

    MACOS = True
except ImportError:  # keeps the pure logic above importable off-macOS
    MACOS = False


if MACOS:
    ACCENT = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.62, 0.93, 0.78, 1.0)
    TEXT_PRIMARY = NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.92)
    TEXT_SECONDARY = NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.5)
    TEXT_FAINT = NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.28)

    WIDGET_W = 292
    PAD = 26
    ROW_H = 34

    def _label(text, font, color, frame, align_left=True):
        f = NSTextField.alloc().initWithFrame_(frame)
        f.setStringValue_(text)
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setEditable_(False)
        f.setSelectable_(False)
        f.setFont_(font)
        f.setTextColor_(color)
        if align_left:
            f.setAlignment_(0)  # NSTextAlignmentLeft
        return f

    def _attr_title(text, font, color):
        style = NSMutableParagraphStyle.alloc().init()
        style.setAlignment_(0)
        style.setLineBreakMode_(4)  # truncate tail
        return AppKit.NSAttributedString.alloc().initWithString_attributes_(
            text,
            {
                AppKit.NSFontAttributeName: font,
                AppKit.NSForegroundColorAttributeName: color,
                AppKit.NSParagraphStyleAttributeName: style,
            },
        )

    class MoodGuardApp(NSObject):
        def applicationDidFinishLaunching_(self, _):
            self.data = load_data()
            self.buildStatusItem()
            self.buildWindow()
            if not self.data.get("widget_hidden"):
                self.window.orderFrontRegardless()
            self.refresh()
            self.timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                3600, self, "hourlyCheck:", None, True
            )
            AppKit.NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                self, "windowMoved:", AppKit.NSWindowDidMoveNotification, None
            )

        # ---------------------------------------------------------- status bar
        def buildStatusItem(self):
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
                AppKit.NSVariableStatusItemLength
            )
            menu = NSMenu.alloc().init()
            for title, action in [
                ("Show / hide widget", "toggleWidget:"),
                ("Customise activities…", "editActivities:"),
                ("View recent activity", "showLog:"),
                (None, None),
                ("Quit MoodGuard", "quitApp:"),
            ]:
                if title is None:
                    menu.addItem_(NSMenuItem.separatorItem())
                    continue
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
                item.setTarget_(self)
                menu.addItem_(item)
            self.status_item.setMenu_(menu)

        # ------------------------------------------------------------- window
        def buildWindow(self):
            h = self.windowHeight()
            self.window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, WIDGET_W, h),
                AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel,
                NSBackingStoreBuffered,
                False,
            )
            self.window.setLevel_(AppKit.NSFloatingWindowLevel)
            self.window.setCollectionBehavior_(
                AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                | AppKit.NSWindowCollectionBehaviorStationary
            )
            self.window.setOpaque_(False)
            self.window.setBackgroundColor_(NSColor.clearColor())
            self.window.setHasShadow_(True)
            self.window.setMovableByWindowBackground_(True)
            self.window.setHidesOnDeactivate_(False)
            self.window.setReleasedWhenClosed_(False)

            pos = self.data.get("widget_pos")
            if pos:
                self.window.setFrameOrigin_(AppKit.NSMakePoint(pos[0], pos[1]))
            else:
                screen = NSScreen.mainScreen().visibleFrame()
                x = screen.origin.x + screen.size.width - WIDGET_W - 28
                y = screen.origin.y + screen.size.height - h - 28
                self.window.setFrameOrigin_(AppKit.NSMakePoint(x, y))

        def windowHeight(self):
            n = len(self.data["activities"])
            return PAD + 30 + 58 + 18 + n * ROW_H + 40 + PAD - 10

        def refresh(self):
            h = self.windowHeight()
            frame = self.window.frame()
            top = frame.origin.y + frame.size.height
            self.window.setFrame_display_(
                NSMakeRect(frame.origin.x, top - h, WIDGET_W, h), True
            )

            glass = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDGET_W, h))
            glass.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
            glass.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
            glass.setState_(AppKit.NSVisualEffectStateActive)
            glass.setWantsLayer_(True)
            glass.layer().setCornerRadius_(22.0)
            glass.layer().setMasksToBounds_(True)
            glass.layer().setBorderWidth_(1.0)
            glass.layer().setBorderColor_(
                NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.12).CGColor()
            )
            self.window.setContentView_(glass)

            y = h - PAD

            y -= 14
            glass.addSubview_(
                _label(
                    "M O O D G U A R D",
                    NSFont.systemFontOfSize_weight_(11, AppKit.NSFontWeightSemibold),
                    TEXT_SECONDARY,
                    NSMakeRect(PAD, y, WIDGET_W - 2 * PAD, 16),
                )
            )

            days = days_since_last_activity(self.data)
            big = "–" if days is None else str(days)
            y -= 52
            glass.addSubview_(
                _label(
                    big,
                    NSFont.systemFontOfSize_weight_(42, AppKit.NSFontWeightThin),
                    ACCENT if (days is not None and days < 7) else TEXT_PRIMARY,
                    NSMakeRect(PAD, y, 70, 50),
                )
            )
            caption = (
                "no check-ins yet"
                if days is None
                else ("recharged today ✨" if days == 0 else "days since last recharge")
            )
            glass.addSubview_(
                _label(
                    caption,
                    NSFont.systemFontOfSize_(11),
                    TEXT_SECONDARY,
                    NSMakeRect(PAD + 62, y + 8, WIDGET_W - PAD - (PAD + 62), 16),
                )
            )

            y -= 16
            divider = AppKit.NSView.alloc().initWithFrame_(
                NSMakeRect(PAD, y, WIDGET_W - 2 * PAD, 1)
            )
            divider.setWantsLayer_(True)
            divider.layer().setBackgroundColor_(
                NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.1).CGColor()
            )
            glass.addSubview_(divider)

            today = date.today().isoformat()
            font = NSFont.systemFontOfSize_(13)
            for i, label in enumerate(self.data["activities"]):
                y -= ROW_H
                done = today in self.data["log"].get(label, [])
                btn = NSButton.alloc().initWithFrame_(
                    NSMakeRect(PAD - 8, y, WIDGET_W - 2 * PAD + 16, ROW_H - 4)
                )
                btn.setBordered_(False)
                btn.setTag_(i)
                btn.setTarget_(self)
                btn.setAction_("toggleActivity:")
                text = ("✓  " + label) if done else label
                color = ACCENT if done else TEXT_PRIMARY
                btn.setAttributedTitle_(_attr_title(text, font, color))
                glass.addSubview_(btn)

            y -= 36
            edit = NSButton.alloc().initWithFrame_(
                NSMakeRect(PAD - 8, y, WIDGET_W - 2 * PAD + 16, 24)
            )
            edit.setBordered_(False)
            edit.setTarget_(self)
            edit.setAction_("editActivities:")
            edit.setAttributedTitle_(
                _attr_title("✎  customise", NSFont.systemFontOfSize_(11), TEXT_FAINT)
            )
            glass.addSubview_(edit)

            self.status_item.button().setTitle_(
                status_icon(days) + ("" if days is None else " {}d".format(days))
            )

        # ------------------------------------------------------------ actions
        def toggleActivity_(self, sender):
            label = self.data["activities"][sender.tag()]
            today = date.today().isoformat()
            entries = self.data["log"].setdefault(label, [])
            if today in entries:
                entries.remove(today)
            else:
                entries.append(today)
            save_data(self.data)
            self.refresh()

        def toggleWidget_(self, _):
            if self.window.isVisible():
                self.window.orderOut_(None)
                self.data["widget_hidden"] = True
            else:
                self.window.orderFrontRegardless()
                self.data["widget_hidden"] = False
            save_data(self.data)

        def windowMoved_(self, note):
            if note.object() is self.window:
                o = self.window.frame().origin
                self.data["widget_pos"] = [o.x, o.y]
                save_data(self.data)

        def editActivities_(self, _):
            NSApp.activateIgnoringOtherApps_(True)
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Customise activities")
            alert.setInformativeText_(
                "One activity per line (up to {}). Start with an emoji if you like. "
                "History for removed lines is kept.".format(MAX_ACTIVITIES)
            )
            alert.addButtonWithTitle_("Save")
            alert.addButtonWithTitle_("Cancel")
            scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 170))
            tv = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 170))
            tv.setString_("\n".join(self.data["activities"]))
            tv.setFont_(NSFont.systemFontOfSize_(13))
            tv.setRichText_(False)
            scroll.setDocumentView_(tv)
            scroll.setHasVerticalScroller_(True)
            alert.setAccessoryView_(scroll)
            alert.window().setInitialFirstResponder_(tv)
            if alert.runModal() == AppKit.NSAlertFirstButtonReturn:
                labels = parse_activity_lines(str(tv.string()))
                if labels:
                    self.data["activities"] = labels
                    for label in labels:
                        self.data["log"].setdefault(label, [])
                    save_data(self.data)
                    self.refresh()

        def showLog_(self, _):
            NSApp.activateIgnoringOtherApps_(True)
            lines = []
            for label in self.data["activities"]:
                entries = sorted(self.data["log"].get(label, []))[-3:]
                lines.append("{}: {}".format(label, ", ".join(entries) if entries else "none yet"))
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Recent activity")
            alert.setInformativeText_("\n".join(lines))
            alert.runModal()

        def hourlyCheck_(self, _):
            self.data = load_data()
            self.refresh()
            days = days_since_last_activity(self.data)
            if days is not None and days >= WARNING_DAYS:
                today = date.today().isoformat()
                if self.data.get("last_warned") != today:
                    send_notification(
                        APP_NAME,
                        "{} days without a recharge".format(days),
                        "Nothing on your recharge list in two weeks. That's usually "
                        "when the low mood creeps in without you noticing why. "
                        "Pick one today.",
                    )
                    self.data["last_warned"] = today
                    save_data(self.data)

        def quitApp_(self, _):
            AppKit.NSApplication.sharedApplication().terminate_(None)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    delegate = MoodGuardApp.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    if not MACOS:
        raise SystemExit("MoodGuard needs macOS (pip3 install --user pyobjc-framework-Cocoa)")
    main()
