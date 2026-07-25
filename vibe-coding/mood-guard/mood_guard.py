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
        NSGradient,
        NSMakeRect,
        NSMenu,
        NSMenuItem,
        NSMutableParagraphStyle,
        NSObject,
        NSPanel,
        NSScreen,
        NSScrollView,
        NSShadow,
        NSStatusBar,
        NSTextField,
        NSTextView,
        NSView,
    )
    from PyObjCTools import AppHelper

    MACOS = True
except ImportError:  # keeps the pure logic above importable off-macOS
    MACOS = False


if MACOS:
    # ---- layout ----
    WIDGET_W = 300
    PAD = 24
    CARD_RADIUS = 28.0
    TITLE_SLOT = 14
    NUMBER_SLOT = 52
    DIVIDER_SLOT = 16
    PILL_H = 52
    ROW_GAP = 10
    PRE_BTN_GAP = 16
    BTN_H = 34

    def _c(r, g, b, a=1.0):
        return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)

    def _w(white, a):
        return NSColor.colorWithCalibratedWhite_alpha_(white, a)

    # warm-to-cool diagonal, in the spirit of Apple's own widget gradients
    GRADIENT = NSGradient.alloc().initWithColors_(
        [
            _c(0.98, 0.82, 0.68),  # warm peach
            _c(0.92, 0.60, 0.63),  # coral pink
            _c(0.58, 0.44, 0.70),  # mauve
            _c(0.22, 0.18, 0.36),  # deep indigo
        ]
    )

    ACCENT = _c(0.80, 0.68, 1.0)  # soft lavender, used for the checked state
    TEXT_PRIMARY = _w(1.0, 0.96)
    TEXT_SECONDARY = _w(1.0, 0.68)
    TEXT_FAINT = _w(1.0, 0.55)

    ROW_FILL = _w(1.0, 0.15)
    ROW_FILL_DONE = _w(1.0, 0.22)
    ROW_BORDER = _w(1.0, 0.24)
    CIRCLE_STROKE = _w(1.0, 0.62)
    CHECK_FILL = ACCENT
    CHECK_MARK = _w(0.12, 1.0)

    TEXT_SHADOW = NSShadow.alloc().init()
    TEXT_SHADOW.setShadowColor_(_w(0.0, 0.45))
    TEXT_SHADOW.setShadowBlurRadius_(3.0)
    TEXT_SHADOW.setShadowOffset_(AppKit.NSMakeSize(0, -1))

    def _attr(text, font, color, align=0):
        style = NSMutableParagraphStyle.alloc().init()
        style.setAlignment_(align)
        style.setLineBreakMode_(4)  # truncate tail
        return AppKit.NSAttributedString.alloc().initWithString_attributes_(
            text,
            {
                AppKit.NSFontAttributeName: font,
                AppKit.NSForegroundColorAttributeName: color,
                AppKit.NSParagraphStyleAttributeName: style,
                AppKit.NSShadowAttributeName: TEXT_SHADOW,
            },
        )

    def _label(text, font, color, frame):
        f = NSTextField.alloc().initWithFrame_(frame)
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setEditable_(False)
        f.setSelectable_(False)
        f.setAttributedStringValue_(_attr(text, font, color))
        return f

    class CardView(NSView):
        """The whole widget's background: a soft gradient clipped to a
        rounded card by the view's own layer (masksToBounds)."""

        def drawRect_(self, rect):
            GRADIENT.drawInRect_angle_(self.bounds(), 55.0)

    class ActivityRow(NSView):
        """One tappable pill: translucent glass, with a circular checkbox
        that fills solid and gets a checkmark once it's done for today."""

        def initWithFrame_(self, frame):
            self = objc.super(ActivityRow, self).initWithFrame_(frame)
            if self is None:
                return None
            self.label = ""
            self.done = False
            self.index = 0
            self.app = None
            return self

        def drawRect_(self, rect):
            b = self.bounds()
            h = b.size.height
            pill = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                b, h / 2.0, h / 2.0
            )
            (ROW_FILL_DONE if self.done else ROW_FILL).setFill()
            pill.fill()
            pill.setLineWidth_(1.0)
            ROW_BORDER.setStroke()
            pill.stroke()

            d = 24.0
            cx = 14.0
            cy = (h - d) / 2.0
            circle = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
                AppKit.NSMakeRect(cx, cy, d, d)
            )
            if self.done:
                CHECK_FILL.setFill()
                circle.fill()
                check = AppKit.NSBezierPath.bezierPath()
                check.moveToPoint_(AppKit.NSMakePoint(cx + d * 0.26, cy + d * 0.52))
                check.lineToPoint_(AppKit.NSMakePoint(cx + d * 0.42, cy + d * 0.34))
                check.lineToPoint_(AppKit.NSMakePoint(cx + d * 0.76, cy + d * 0.66))
                check.setLineWidth_(2.2)
                check.setLineCapStyle_(AppKit.NSRoundLineCapStyle)
                check.setLineJoinStyle_(AppKit.NSRoundLineJoinStyle)
                CHECK_MARK.setStroke()
                check.stroke()
            else:
                circle.setLineWidth_(1.6)
                CIRCLE_STROKE.setStroke()
                circle.stroke()

            attr = _attr(self.label, NSFont.systemFontOfSize_weight_(14, AppKit.NSFontWeightMedium), TEXT_PRIMARY)
            size = attr.size()
            text_x = cx + d + 12
            text_y = (h - size.height) / 2.0
            attr.drawAtPoint_(AppKit.NSMakePoint(text_x, text_y))

        def mouseDown_(self, event):
            if self.app is not None:
                self.app.toggleActivity_(self.index)

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
            rows = n * PILL_H + max(0, n - 1) * ROW_GAP
            return (
                2 * PAD
                + TITLE_SLOT
                + NUMBER_SLOT
                + DIVIDER_SLOT
                + rows
                + PRE_BTN_GAP
                + BTN_H
            )

        def refresh(self):
            h = self.windowHeight()
            frame = self.window.frame()
            top = frame.origin.y + frame.size.height
            self.window.setFrame_display_(
                NSMakeRect(frame.origin.x, top - h, WIDGET_W, h), True
            )

            card = CardView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDGET_W, h))
            card.setWantsLayer_(True)
            card.layer().setCornerRadius_(CARD_RADIUS)
            card.layer().setMasksToBounds_(True)
            card.layer().setBorderWidth_(1.0)
            card.layer().setBorderColor_(_w(1.0, 0.28).CGColor())
            self.window.setContentView_(card)

            y = h - PAD

            y -= TITLE_SLOT
            card.addSubview_(
                _label(
                    "M O O D G U A R D",
                    NSFont.systemFontOfSize_weight_(11, AppKit.NSFontWeightSemibold),
                    TEXT_SECONDARY,
                    NSMakeRect(PAD, y, WIDGET_W - 2 * PAD, 16),
                )
            )

            days = days_since_last_activity(self.data)
            big = "–" if days is None else str(days)
            y -= NUMBER_SLOT
            card.addSubview_(
                _label(
                    big,
                    NSFont.systemFontOfSize_weight_(40, AppKit.NSFontWeightThin),
                    TEXT_PRIMARY,
                    NSMakeRect(PAD, y, 70, 50),
                )
            )
            caption = (
                "no check-ins yet"
                if days is None
                else ("recharged today ✨" if days == 0 else "days since last recharge")
            )
            card.addSubview_(
                _label(
                    caption,
                    NSFont.systemFontOfSize_(11),
                    TEXT_SECONDARY,
                    NSMakeRect(PAD + 60, y + 6, WIDGET_W - PAD - (PAD + 60), 32),
                )
            )

            y -= DIVIDER_SLOT
            divider = NSView.alloc().initWithFrame_(
                NSMakeRect(PAD, y + 8, WIDGET_W - 2 * PAD, 1)
            )
            divider.setWantsLayer_(True)
            divider.layer().setBackgroundColor_(_w(1.0, 0.16).CGColor())
            card.addSubview_(divider)

            today = date.today().isoformat()
            for i, label in enumerate(self.data["activities"]):
                if i > 0:
                    y -= ROW_GAP
                y -= PILL_H
                row = ActivityRow.alloc().initWithFrame_(
                    NSMakeRect(PAD, y, WIDGET_W - 2 * PAD, PILL_H)
                )
                row.label = label
                row.done = today in self.data["log"].get(label, [])
                row.index = i
                row.app = self
                card.addSubview_(row)

            y -= PRE_BTN_GAP
            y -= BTN_H
            edit = NSButton.alloc().initWithFrame_(NSMakeRect(PAD, y, WIDGET_W - 2 * PAD, BTN_H))
            edit.setBordered_(False)
            edit.setWantsLayer_(True)
            edit.layer().setBackgroundColor_(_w(1.0, 0.14).CGColor())
            edit.layer().setCornerRadius_(BTN_H / 2.0)
            edit.setTarget_(self)
            edit.setAction_("editActivities:")
            edit.setAttributedTitle_(
                _attr(
                    "Customise",
                    NSFont.systemFontOfSize_weight_(12, AppKit.NSFontWeightMedium),
                    TEXT_FAINT,
                    align=2,  # centered
                )
            )
            card.addSubview_(edit)

            self.status_item.button().setTitle_(
                status_icon(days) + ("" if days is None else " {}d".format(days))
            )

        # ------------------------------------------------------------ actions
        def toggleActivity_(self, index):
            label = self.data["activities"][index]
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
