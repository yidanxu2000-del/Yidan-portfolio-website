#!/usr/bin/env python3
"""Job Copilot.

    python3 run.py                 open the app (this is the one you want)
    python3 run.py sweep           discover + analyse, no UI — good in a cron job
    python3 run.py discover        fetch from configured sources only
    python3 run.py analyse [N]     score up to N unscored roles (default 25)
    python3 run.py draft [N]       draft the top N unscored-but-eligible roles
    python3 run.py where           print where the data lives

Sending is never triggered from the command line. It happens in the app, one
application at a time, behind an explicit approval.
"""

from __future__ import annotations

import sys

from jobcopilot.config import DATA_DIR, load_config
from jobcopilot.pipeline import analyse_pending, prepare_top, run_discovery
from jobcopilot.server import serve


def _print_notes(label: str, notes: list[str]) -> None:
    if notes:
        print(f"  {label}:")
        for note in notes:
            print(f"    - {note}")


def cmd_discover(cfg) -> None:
    out = run_discovery(cfg)
    print(
        f"  found {out['found']}, kept {out['found'] - out['filtered_out']}, "
        f"{out['new']} new, {out['updated']} updated"
    )
    _print_notes("notes", out["notes"])


def cmd_analyse(cfg, limit: int) -> None:
    out = analyse_pending(cfg, limit=limit)
    print(f"  scored {out['analysed']}")
    for row in out["results"][:15]:
        print(f"    {row['fit_score']:>3}  {row['company'][:28]:<28} {row['title'][:44]}")
    _print_notes("errors", out["errors"])


def cmd_draft(cfg, limit: int) -> None:
    out = prepare_top(cfg, limit=limit)
    for row in out["prepared"]:
        print(f"    drafted {row['fit_score']:>3}  {row['company']} — {row['title']}")
    if not out["prepared"]:
        print("  nothing eligible — analyse some roles first, or lower min_score_to_draft")
    _print_notes("errors", out["errors"])


def main(argv: list[str]) -> int:
    try:
        cfg = load_config()
    except ValueError as exc:
        print(f"  config error: {exc}", file=sys.stderr)
        return 2

    command = argv[0] if argv else "serve"
    count = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else None

    if command in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if command == "where":
        print(f"  data:        {DATA_DIR}")
        print(f"  documents:   {DATA_DIR / 'out'}")
        print(f"  attachments: {DATA_DIR / 'attachments'}")
        return 0
    if command == "serve":
        serve(cfg)
        return 0
    if command == "discover":
        cmd_discover(cfg)
        return 0
    if command == "analyse":
        cmd_analyse(cfg, count or 25)
        return 0
    if command == "draft":
        cmd_draft(cfg, count or 5)
        return 0
    if command == "sweep":
        cmd_discover(cfg)
        cmd_analyse(cfg, count or 40)
        return 0

    print(f"  unknown command: {command}\n", file=sys.stderr)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
