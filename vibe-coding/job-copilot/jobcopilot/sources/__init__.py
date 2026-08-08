"""Job sources, and the sweep that runs all the configured ones."""

from __future__ import annotations

from . import ats, boards, linkedin, manual
from .base import safe_collect

__all__ = ["ats", "boards", "linkedin", "manual", "discover"]


def discover(cfg) -> tuple[list[dict], list[str]]:
    """Run every configured source. Returns (jobs, notes about what failed).

    A source that's down or misconfigured produces a note, not an exception —
    one dead board shouldn't cost you the rest of the sweep.
    """
    jobs: list[dict] = []
    notes: list[str] = []
    src = cfg.sources

    for provider, tokens in (
        ("greenhouse", src.greenhouse),
        ("lever", src.lever),
        ("ashby", src.ashby),
        ("workable", src.workable),
        ("smartrecruiters", src.smartrecruiters),
        ("recruitee", src.recruitee),
    ):
        for token in tokens:
            found, err = safe_collect(
                f"{provider}:{token}", ats.PROVIDERS[provider], token
            )
            jobs += found
            if err:
                notes.append(err)

    for query in src.remotive_queries:
        found, err = safe_collect(f"remotive:{query}", boards.remotive, query)
        jobs += found
        if err:
            notes.append(err)

    if src.arbeitnow:
        found, err = safe_collect("arbeitnow", boards.arbeitnow)
        jobs += found
        if err:
            notes.append(err)

    for query in src.jobicy_queries:
        found, err = safe_collect(f"jobicy:{query}", boards.jobicy, query)
        jobs += found
        if err:
            notes.append(err)

    if src.adzuna_app_id and src.adzuna_app_key:
        for query in src.adzuna_queries:
            found, err = safe_collect(
                f"adzuna:{query}",
                boards.adzuna,
                src.adzuna_app_id,
                src.adzuna_app_key,
                src.adzuna_country,
                query,
            )
            jobs += found
            if err:
                notes.append(err)
    elif src.adzuna_queries:
        notes.append("adzuna: queries configured but no app id/key")

    if cfg.linkedin.alerts_enabled:
        found, err = safe_collect("linkedin:alerts", linkedin.from_alert_emails, cfg)
        jobs += found
        if err:
            notes.append(err)

    if cfg.linkedin.assisted_enabled:
        found, err = safe_collect(
            "linkedin:assisted", linkedin.from_assisted_search, cfg
        )
        jobs += found
        if err:
            notes.append(err)

    if not jobs and not notes:
        notes.append(
            "No sources configured. Add company board tokens or job queries to "
            "config.toml — see config.example.toml."
        )
    return jobs, notes
