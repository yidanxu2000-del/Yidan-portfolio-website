"""Flat-file JSON store. One file per collection, whole-file rewrites.

Small enough dataset that this is simpler and more inspectable than a database —
you can open data/jobs.json and read it.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR

_LOCK = threading.RLock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{name}.json"


def _read(name: str, default: Any) -> Any:
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text("utf-8"))
    except json.JSONDecodeError:
        # Don't destroy a corrupt file — move it aside so it can be inspected.
        p.rename(p.with_suffix(f".corrupt-{int(datetime.now().timestamp())}.json"))
        return default


def _write(name: str, value: Any) -> None:
    p = _path(name)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Store:
    """jobs, analyses and applications, each keyed by job id."""

    def jobs(self) -> dict[str, dict]:
        with _LOCK:
            return _read("jobs", {})

    def job(self, job_id: str) -> dict | None:
        return self.jobs().get(job_id)

    def upsert_jobs(self, jobs: list[dict]) -> tuple[int, int]:
        """Returns (new, updated). Never overwrites discovered_at."""
        with _LOCK:
            existing = _read("jobs", {})
            new = updated = 0
            for job in jobs:
                jid = job["id"]
                if jid in existing:
                    job["discovered_at"] = existing[jid].get("discovered_at", now())
                    if existing[jid] != {**existing[jid], **job}:
                        updated += 1
                    existing[jid] = {**existing[jid], **job}
                else:
                    job.setdefault("discovered_at", now())
                    existing[jid] = job
                    new += 1
            _write("jobs", existing)
            return new, updated

    def analyses(self) -> dict[str, dict]:
        with _LOCK:
            return _read("analyses", {})

    def analysis(self, job_id: str) -> dict | None:
        return self.analyses().get(job_id)

    def put_analysis(self, job_id: str, analysis: dict) -> None:
        with _LOCK:
            data = _read("analyses", {})
            data[job_id] = {**analysis, "analysed_at": now()}
            _write("analyses", data)

    def applications(self) -> dict[str, dict]:
        with _LOCK:
            return _read("applications", {})

    def application(self, job_id: str) -> dict | None:
        return self.applications().get(job_id)

    def put_application(self, job_id: str, app: dict) -> dict:
        with _LOCK:
            data = _read("applications", {})
            prev = data.get(job_id, {})
            merged = {**prev, **app}
            merged.setdefault("job_id", job_id)
            merged.setdefault("status", "draft")
            merged.setdefault("events", [])
            merged["updated_at"] = now()
            data[job_id] = merged
            _write("applications", data)
            return merged

    def log_event(self, job_id: str, kind: str, note: str = "") -> None:
        with _LOCK:
            data = _read("applications", {})
            app = data.setdefault(
                job_id, {"job_id": job_id, "status": "draft", "events": []}
            )
            app.setdefault("events", []).append(
                {"at": now(), "kind": kind, "note": note}
            )
            _write("applications", data)

    def sent_today(self) -> int:
        today = now()[:10]
        return sum(
            1
            for app in self.applications().values()
            if app.get("sent_at", "").startswith(today)
        )

    def profile(self) -> dict | None:
        with _LOCK:
            return _read("profile", None)

    def put_profile(self, profile: dict) -> None:
        with _LOCK:
            _write("profile", profile)
