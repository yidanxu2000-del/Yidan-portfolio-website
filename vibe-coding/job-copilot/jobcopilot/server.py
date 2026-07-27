"""Local web app. Stdlib HTTP server, JSON API, static files from web/.

Binds to localhost. Nothing here is hardened for exposure to a network, and it
doesn't need to be — it's a tool that runs on your own machine.
"""

from __future__ import annotations

import json
import traceback
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import pipeline
from .analyze import analyse
from .config import DATA_DIR, Config
from .letter import edit_letter
from .llm import Claude, LLMUnavailable
from .outreach import ATTACHMENTS_DIR, SendBlocked, preflight, send
from .profile import DEFAULT_PROFILE, load_profile, save_profile
from .render import relative_out, write_documents
from .sources import manual
from .store import Store, now
from .tailor import tailor_resume

WEB_DIR = Path(__file__).parent / "web"
OUT_DIR = DATA_DIR / "out"

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    server_version = "job-copilot"
    cfg: Config

    # --- plumbing ---------------------------------------------------------

    def log_message(self, fmt: str, *args) -> None:
        # One tidy line per request instead of the default noise.
        print(f"  {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(f"Malformed JSON body: {exc}") from exc

    def _static(self, path: str) -> None:
        name = path.lstrip("/") or "index.html"
        target = (WEB_DIR / name).resolve()
        if not target.is_relative_to(WEB_DIR.resolve()) or not target.is_file():
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        self._send(
            200,
            target.read_bytes(),
            _MIME.get(target.suffix, "application/octet-stream"),
        )

    def _serve_out(self, path: str) -> None:
        """Serve rendered resumes and letters so they can be previewed in a tab."""
        name = path[len("/out/"):]
        target = (OUT_DIR / name).resolve()
        if not target.is_relative_to(OUT_DIR.resolve()) or not target.is_file():
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        self._send(200, target.read_bytes(), _MIME.get(target.suffix, "text/plain"))

    # --- routing ----------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/"):
                self._json(self._get_api(parsed.path, parse_qs(parsed.query)))
            elif parsed.path.startswith("/out/"):
                self._serve_out(parsed.path)
            else:
                self._static(parsed.path)
        except ApiError as exc:
            self._json({"error": str(exc)}, exc.status)
        except Exception as exc:
            traceback.print_exc()
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    do_HEAD = do_GET

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            self._json(self._post_api(parsed.path, self._body()))
        except ApiError as exc:
            self._json({"error": str(exc)}, exc.status)
        except (SendBlocked, LLMUnavailable) as exc:
            self._json({"error": str(exc)}, 400)
        except KeyError as exc:
            self._json({"error": f"Not found: {exc}"}, 404)
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:
            traceback.print_exc()
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    # --- GET endpoints ----------------------------------------------------

    def _get_api(self, path: str, query: dict) -> dict:
        store = Store()
        if path == "/api/state":
            return self._state(store)
        if path == "/api/profile":
            return {"profile": load_profile(), "default": DEFAULT_PROFILE}
        if path == "/api/job":
            job_id = (query.get("job_id") or [""])[0]
            job = store.job(job_id)
            if not job:
                raise ApiError("Unknown job", 404)
            return {
                "job": job,
                "analysis": store.analysis(job_id),
                "application": store.application(job_id),
            }
        if path == "/api/preflight":
            job_id = (query.get("job_id") or [""])[0]
            app = store.application(job_id) or {}
            to_email = (app.get("contact") or {}).get("email", "")
            return {
                "problems": preflight(self.cfg, to_email, store.sent_today()),
                "sent_today": store.sent_today(),
                "daily_cap": self.cfg.send.daily_cap,
                "mode": self.cfg.send.mode,
                "attachments_dir": str(ATTACHMENTS_DIR),
                "available_attachments": sorted(
                    p.name
                    for p in ATTACHMENTS_DIR.glob("*")
                    if p.is_file() and not p.name.startswith(".")
                )
                if ATTACHMENTS_DIR.exists()
                else [],
            }
        raise ApiError("Unknown endpoint", 404)

    def _state(self, store: Store) -> dict:
        jobs = store.jobs()
        analyses = store.analyses()
        applications = store.applications()
        rows = []
        for job_id, job in jobs.items():
            analysis = analyses.get(job_id) or {}
            app = applications.get(job_id) or {}
            rows.append(
                {
                    "id": job_id,
                    "company": job.get("company", ""),
                    "title": job.get("title", ""),
                    "location": job.get("location", ""),
                    "source": job.get("source", ""),
                    "url": job.get("url", ""),
                    "discovered_at": job.get("discovered_at", ""),
                    "needs_detail": bool(job.get("extra", {}).get("needs_detail"))
                    or not (job.get("description") or "").strip(),
                    "fit_score": analysis.get("fit_score"),
                    "verdict": analysis.get("verdict"),
                    "engine": analysis.get("engine"),
                    "one_line": analysis.get("one_line", ""),
                    "sponsorship": (analysis.get("work_authorisation") or {}).get("stance"),
                    "status": app.get("status"),
                    "has_draft": bool(app.get("letter")),
                }
            )
        rows.sort(
            key=lambda r: (r["fit_score"] if r["fit_score"] is not None else -1),
            reverse=True,
        )
        return {
            "jobs": rows,
            "counts": {
                "total": len(rows),
                "analysed": len(analyses),
                "drafts": sum(1 for a in applications.values() if a.get("letter")),
                "sent": sum(1 for a in applications.values() if a.get("sent_at")),
                "needs_detail": sum(1 for r in rows if r["needs_detail"]),
            },
            "config": {
                "model": self.cfg.model,
                "llm_available": Claude(self.cfg).available,
                "send_mode": self.cfg.send.mode,
                "min_score_to_draft": self.cfg.min_score_to_draft,
                "sent_today": store.sent_today(),
                "daily_cap": self.cfg.send.daily_cap,
            },
        }

    # --- POST endpoints ---------------------------------------------------

    def _post_api(self, path: str, body: dict) -> dict:
        store = Store()
        cfg = self.cfg

        if path == "/api/discover":
            return pipeline.run_discovery(cfg)

        if path == "/api/analyse":
            return pipeline.analyse_pending(
                cfg, limit=int(body.get("limit", 25)), force=bool(body.get("force"))
            )

        if path == "/api/analyse-one":
            job = self._require_job(store, body)
            analysis = analyse(job, load_profile(), Claude(cfg))
            store.put_analysis(job["id"], analysis)
            return {"analysis": analysis}

        if path == "/api/job/paste":
            job = manual.from_paste(
                title=body.get("title", ""),
                company=body.get("company", ""),
                description=body.get("description", ""),
                url=body.get("url", ""),
                location=body.get("location", ""),
                apply_email=body.get("apply_email", ""),
            )
            store.upsert_jobs([job])
            return {"job": job}

        if path == "/api/job/url":
            url = (body.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                raise ApiError("A http(s) URL is required.")
            job = manual.from_url(url)
            store.upsert_jobs([job])
            return {"job": job}

        if path == "/api/job/detail":
            job = self._require_job(store, body)
            description = (body.get("description") or "").strip()
            if not description:
                raise ApiError("A description is required.")
            job["description"] = description
            job.setdefault("extra", {})["needs_detail"] = False
            if body.get("company"):
                job["company"] = body["company"]
            store.upsert_jobs([job])
            return {"job": job}

        if path == "/api/prepare":
            job = self._require_job(store, body)
            return {"application": pipeline.prepare_application(
                cfg, job["id"], body.get("contact") or {}
            )}

        if path == "/api/prepare-top":
            return pipeline.prepare_top(cfg, limit=int(body.get("limit", 5)))

        if path == "/api/resume/retailor":
            job = self._require_job(store, body)
            profile = load_profile()
            analysis = store.analysis(job["id"]) or {}
            resume = tailor_resume(job, profile, analysis, Claude(cfg))
            app = store.application(job["id"]) or {}
            files = write_documents(profile, job, resume, app.get("letter"))
            return {
                "application": store.put_application(
                    job["id"], {"resume": resume, "files": {**app.get("files", {}), **files}}
                )
            }

        if path == "/api/letter/edit":
            job = self._require_job(store, body)
            app = store.application(job["id"])
            if not app or not app.get("letter"):
                raise ApiError("No draft letter yet — prepare the application first.")
            profile = load_profile()
            letter = edit_letter(
                app["letter"], job, profile, body.get("instruction", ""), Claude(cfg)
            )
            files = write_documents(profile, job, app.get("resume"), letter)
            return {
                "application": store.put_application(
                    job["id"],
                    {"letter": letter, "files": {**app.get("files", {}), **files}},
                )
            }

        if path == "/api/letter/save":
            job = self._require_job(store, body)
            app = store.application(job["id"]) or {}
            letter = {**(app.get("letter") or {})}
            letter["subject"] = body.get("subject", letter.get("subject", ""))
            letter["body"] = body.get("body", letter.get("body", ""))
            letter["engine"] = "hand-edited"
            profile = load_profile()
            files = write_documents(profile, job, app.get("resume"), letter)
            return {
                "application": store.put_application(
                    job["id"],
                    {"letter": letter, "files": {**app.get("files", {}), **files}},
                )
            }

        if path == "/api/application/contact":
            job = self._require_job(store, body)
            return {
                "application": store.put_application(
                    job["id"],
                    {
                        "contact": {
                            "name": body.get("name", ""),
                            "email": body.get("email", ""),
                        }
                    },
                )
            }

        if path == "/api/application/status":
            job = self._require_job(store, body)
            status = body.get("status", "")
            allowed = {
                "draft", "approved", "sent", "skipped",
                "replied", "interview", "rejected", "offer",
            }
            if status not in allowed:
                raise ApiError(f"status must be one of {sorted(allowed)}")
            store.log_event(job["id"], "status", status)
            return {"application": store.put_application(job["id"], {"status": status})}

        if path == "/api/send":
            return self._send_application(store, body)

        if path == "/api/profile":
            profile = body.get("profile")
            if not isinstance(profile, dict) or not profile.get("name"):
                raise ApiError("A profile object with a name is required.")
            return {"profile": save_profile(profile)}

        raise ApiError("Unknown endpoint", 404)

    def _require_job(self, store: Store, body: dict) -> dict:
        job = store.job((body.get("job_id") or "").strip())
        if not job:
            raise ApiError("Unknown job", 404)
        return job

    def _send_application(self, store: Store, body: dict) -> dict:
        job = self._require_job(store, body)
        app = store.application(job["id"]) or {}
        letter = app.get("letter") or {}
        if not letter.get("body"):
            raise ApiError("No letter to send — prepare the application first.")
        if not body.get("approved"):
            raise ApiError("Approval is required. Nothing was sent.")

        contact = {
            "name": body.get("to_name", (app.get("contact") or {}).get("name", "")),
            "email": body.get("to_email", (app.get("contact") or {}).get("email", "")),
        }
        result = send(
            self.cfg,
            to_email=contact["email"],
            to_name=contact["name"],
            subject=body.get("subject") or letter.get("subject", ""),
            body_markdown=letter.get("body", ""),
            attachments=list(body.get("attachments") or []),
            sent_today=store.sent_today(),
            approved=True,
        )
        store.log_event(job["id"], "sent", f"to {contact['email']}")
        return {
            "sent": result,
            "application": store.put_application(
                job["id"],
                {"status": "sent", "sent_at": now(), "contact": contact},
            ),
        }


def serve(cfg: Config) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    handler = partial(Handler)
    Handler.cfg = cfg
    try:
        httpd = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    except OSError as exc:
        if exc.errno in (48, 98):  # EADDRINUSE on macOS / Linux
            raise SystemExit(
                f"  Port {cfg.port} is already in use — Job Copilot may already be "
                f"running at http://{cfg.host}:{cfg.port}\n"
                f"  If not, change `port` in config.toml."
            ) from exc
        raise
    url = f"http://{cfg.host}:{cfg.port}"

    llm = "Claude " + cfg.model if Claude(cfg).available else "no API key (keyword mode)"
    print(f"\n  Job Copilot — {url}")
    print(f"  analysis: {llm}")
    print(f"  sending:  {cfg.send.mode}"
          + ("  (nothing will be sent)" if cfg.send.mode == "review" else ""))
    print("  ctrl-c to stop\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        httpd.server_close()
