#!/usr/bin/env python3
"""MoodGuard — a menu-bar check-in for the things that actually recharge you.

Tracks seven activities. If none of them happen for 14 days in a row, it
fires a macOS notification — the idea being to catch the drift toward a low
mood *before* it arrives, not explain it after the fact.
"""
import json
import os
import subprocess
from datetime import date, datetime

import rumps

APP_NAME = "MoodGuard"
DATA_DIR = os.path.expanduser("~/Library/Application Support/MoodGuard")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
WARNING_DAYS = 14

ACTIVITIES = [
    ("date", "💛 Saw my boyfriend, 3+ hours"),
    ("pet", "🐾 Long time with a cat or dog"),
    ("food", "🍽️ Restaurant, real food"),
    ("travel", "✈️ Travel"),
    ("social", "🗣️ Meet new people, talk a lot"),
    ("win", "🏆 Big win at work"),
    ("swim", "🏊 Swim"),
]


def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"log": {key: [] for key, _ in ACTIVITIES}, "last_warned": None}
    else:
        with open(DATA_FILE) as f:
            data = json.load(f)
    for key, _ in ACTIVITIES:
        data.setdefault("log", {}).setdefault(key, [])
    data.setdefault("last_warned", None)
    return data


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def days_since_last_activity(data):
    all_dates = [d for entries in data["log"].values() for d in entries]
    if not all_dates:
        return None
    last = max(datetime.strptime(d, "%Y-%m-%d").date() for d in all_dates)
    return (date.today() - last).days


def status_icon(days):
    if days is None:
        return "🙂"  # no history yet — nothing to warn about, just getting started
    if days >= WARNING_DAYS:
        return "🚨"
    if days >= WARNING_DAYS - 3:
        return "⚠️"
    if days >= 7:
        return "😐"
    return "🙂"


def send_notification(title, subtitle, message):
    # osascript (a signed, trusted system binary) posts the notification on
    # our behalf — an unsigned python script calling the notification APIs
    # directly gets silently dropped on modern macOS, this doesn't
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    script = 'display notification "{}" with title "{}" subtitle "{}"'.format(
        esc(message), esc(title), esc(subtitle)
    )
    subprocess.run(["osascript", "-e", script], check=False)


class MoodGuardApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title="🙂")
        self.data = load_data()
        self.item_menu = {}
        for key, label in ACTIVITIES:
            item = rumps.MenuItem(label, callback=self.toggle_today)
            item.key = key
            self.item_menu[key] = item
        self.menu = list(self.item_menu.values()) + [
            None,
            rumps.MenuItem("View recent activity", callback=self.show_log),
        ]
        self.refresh_checks()
        self.refresh_title()

    def toggle_today(self, sender):
        today_str = date.today().isoformat()
        entries = self.data["log"][sender.key]
        if today_str in entries:
            entries.remove(today_str)
            sender.state = False
        else:
            entries.append(today_str)
            sender.state = True
        save_data(self.data)
        self.refresh_title()

    def refresh_checks(self):
        today_str = date.today().isoformat()
        for key, item in self.item_menu.items():
            item.state = today_str in self.data["log"][key]

    def refresh_title(self):
        days = days_since_last_activity(self.data)
        suffix = "" if days is None else " {}d".format(days)
        self.title = "{}{}".format(status_icon(days), suffix)

    def show_log(self, _):
        lines = []
        for key, label in ACTIVITIES:
            entries = sorted(self.data["log"][key])[-3:]
            lines.append("{}: {}".format(label, ", ".join(entries) if entries else "none yet"))
        rumps.alert(title="Recent activity", message="\n".join(lines))

    @rumps.timer(60 * 60)
    def check_warning(self, _):
        self.data = load_data()
        self.refresh_checks()
        self.refresh_title()
        days = days_since_last_activity(self.data)
        if days is not None and days >= WARNING_DAYS:
            today_str = date.today().isoformat()
            if self.data.get("last_warned") != today_str:
                send_notification(
                    "MoodGuard",
                    "14 days without a recharge",
                    "No dates, pets, travel, big wins, food, swims or real talk logged "
                    "in two weeks — that's usually when the low mood creeps in without "
                    "you noticing why. Pick one today.",
                )
                self.data["last_warned"] = today_str
                save_data(self.data)


if __name__ == "__main__":
    MoodGuardApp().run()
