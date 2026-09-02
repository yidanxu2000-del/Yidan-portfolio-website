"""The sweep: discover, pre-filter, analyse, and draft the ones worth drafting."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from . import sources
from .analyze import analyse
from .config import Config
from .letter import draft_letter
from .llm import Claude, LLMUnavailable
from .profile import load_profile
from .render import write_documents
from .store import Store
from .tailor import tailor_resume

# Relevance is decided on the title alone. The description is useless as a filter:
# at a design company every posting mentions design, so a lawyer's job spec at
# Figma reads as a match. The title is what the employer chose to call the job.
#
# The cost of being strict is missing an oddly-titled role — which is what the
# add-by-URL and paste paths are for.
_TITLE_REJECT = re.compile(
    r"\b(sales|account executive|account manager|customer success|customer enablement|"
    r"solutions consultant|recruiter|recruiting|talent|compensation|counsel|legal|"
    r"accountant|accounting|payroll|tax|audit|controller|"
    r"data scien\w*|data engineer|machine learning engineer|scientist|"
    r"software engineer|backend|back-end|frontend engineer|full-?stack|devops|"
    r"site reliability|security engineer|it support|"
    r"marketing|communications|public relations|events?|community manager|"
    r"executive assistant|office manager|facilities|"
    r"nurse|driver|warehouse|solicitor|paralegal|teacher|chef|security guard|"
    r"cleaner|electrician|welder|plumber|barista|forklift|care assistant)\b",
    re.I,
)
# A design, product or research role — the families in her target list.
_ROLE_HINT = re.compile(
    r"\b(design(?:er|ing)?|ux|ui|uiux|user experience|user interface|interaction|"
    r"hmi|human[- ]machine|product manager|product owner|product lead|"
    r"user research(?:er)?|design research(?:er)?|creative director|art director|"
    r"brand designer|design technologist|prototyp\w+|"
    r"head of design|design systems?|content design(?:er)?)\b",
    re.I,
)


def prefilter(jobs: list[dict]) -> tuple[list[dict], int]:
    """Drop obvious non-matches before spending a model call on them.

    A company board lists the whole company — Figma's board is mostly sales, data
    science and support roles — so relevance is required on every source, not just
    the aggregators. A title has to carry a design, product or research signal and
    must not be headed by a different discipline: "Executive Assistant, Design"
    and "Data Scientist, Marketing" both mention the right words and are neither.
    """
    kept = []
    for job in jobs:
        # Anything added by hand or by URL was a deliberate choice. Never drop it.
        if job.get("source", "").split(":")[0] in ("manual", "url"):
            kept.append(job)
            continue
        title = job.get("title", "")
        if _TITLE_REJECT.search(title):
            continue
        if _ROLE_HINT.search(title):
            kept.append(job)
    return kept, len(jobs) - len(kept)


def run_discovery(cfg: Config) -> dict:
    """Fetch from every configured source and store what's new."""
    store = Store()
    found, notes = sources.discover(cfg)
    kept, dropped = prefilter(found)
    new, updated = store.upsert_jobs(kept)
    return {
        "found": len(found),
        "filtered_out": dropped,
        "new": new,
        "updated": updated,
        "notes": notes,
    }


def analyse_pending(cfg: Config, limit: int = 25, force: bool = False) -> dict:
    """Analyse jobs that haven't been assessed yet.

    Runs a few at a time — the calls are independent and this is the difference
    between a sweep finishing in a minute and in ten.
    """
    store = Store()
    profile = load_profile()
    claude = Claude(cfg)

    jobs = store.jobs()
    analyses = store.analyses()
    todo = [
        job
        for job in jobs.values()
        if (force or job["id"] not in analyses)
        and (job.get("description") or "").strip()
    ]
    todo.sort(key=lambda j: j.get("discovered_at", ""), reverse=True)
    todo = todo[:limit]

    results: list[dict] = []
    errors: list[str] = []

    def work(job: dict) -> tuple[dict, dict | None, str | None]:
        try:
            return job, analyse(job, profile, claude), None
        except LLMUnavailable as exc:
            return job, None, f"{job.get('company', '')} — {exc}"
        except Exception as exc:  # a single bad posting shouldn't stop the batch
            return job, None, f"{job.get('company', '')} — {type(exc).__name__}: {exc}"

    workers = 4 if claude.available else 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for job, analysis, err in pool.map(work, todo):
            if err:
                errors.append(err)
                continue
            store.put_analysis(job["id"], analysis)
            results.append(
                {
                    "job_id": job["id"],
                    "company": job.get("company", ""),
                    "title": job.get("title", ""),
                    "fit_score": analysis.get("fit_score", 0),
                    "verdict": analysis.get("verdict", ""),
                }
            )

    results.sort(key=lambda r: r["fit_score"], reverse=True)
    return {"analysed": len(results), "results": results, "errors": errors}


def prepare_application(cfg: Config, job_id: str, contact: dict | None = None) -> dict:
    """Tailor a resume, draft a letter, render both. Sends nothing."""
    store = Store()
    profile = load_profile()
    claude = Claude(cfg)

    job = store.job(job_id)
    if not job:
        raise KeyError(f"Unknown job {job_id}")

    analysis = store.analysis(job_id)
    if not analysis:
        analysis = analyse(job, profile, claude)
        store.put_analysis(job_id, analysis)

    resume = tailor_resume(job, profile, analysis, claude)
    letter = draft_letter(job, profile, analysis, claude, contact)
    files = write_documents(profile, job, resume, letter)

    app = store.put_application(
        job_id,
        {
            "status": "draft",
            "resume": resume,
            "letter": letter,
            "contact": contact or {},
            "files": files,
        },
    )
    store.log_event(job_id, "prepared", f"resume + letter drafted ({resume.get('engine')})")
    return app


def prepare_top(cfg: Config, limit: int = 5) -> dict:
    """Prepare drafts for the highest-scoring jobs that don't have one yet."""
    store = Store()
    analyses = store.analyses()
    applications = store.applications()

    candidates = [
        (job_id, a)
        for job_id, a in analyses.items()
        if a.get("fit_score", 0) >= cfg.min_score_to_draft
        and job_id not in applications
        and store.job(job_id)
    ]
    candidates.sort(key=lambda pair: pair[1].get("fit_score", 0), reverse=True)

    prepared, errors = [], []
    for job_id, analysis in candidates[:limit]:
        try:
            prepare_application(cfg, job_id)
            job = store.job(job_id) or {}
            prepared.append(
                {
                    "job_id": job_id,
                    "company": job.get("company", ""),
                    "title": job.get("title", ""),
                    "fit_score": analysis.get("fit_score", 0),
                }
            )
        except Exception as exc:
            errors.append(f"{job_id}: {type(exc).__name__}: {exc}")
    return {"prepared": prepared, "errors": errors}
