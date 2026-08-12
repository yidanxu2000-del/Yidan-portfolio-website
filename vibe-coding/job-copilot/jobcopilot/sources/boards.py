"""Aggregator job APIs. Wider net than company boards, lower signal.

Remotive, Arbeitnow and Jobicy are open. Adzuna needs a free app id and key
from developer.adzuna.com and covers ordinary UK listings, which the
remote-focused boards miss.
"""

from __future__ import annotations

import urllib.parse

from .base import fetch_json, html_to_text, make_job


def remotive(query: str) -> list[dict]:
    url = "https://remotive.com/api/remote-jobs?limit=50&search=" + urllib.parse.quote(query)
    data = fetch_json(url)
    jobs = []
    for item in (data or {}).get("jobs", []):
        jobs.append(
            make_job(
                source="remotive",
                company=item.get("company_name", ""),
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=html_to_text(item.get("description", "")),
                location=item.get("candidate_required_location", ""),
                remote=True,
                posted_at=item.get("publication_date", ""),
            )
        )
    return jobs


def arbeitnow() -> list[dict]:
    data = fetch_json("https://www.arbeitnow.com/api/job-board-api")
    jobs = []
    for item in (data or {}).get("data", []):
        jobs.append(
            make_job(
                source="arbeitnow",
                company=item.get("company_name", ""),
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=html_to_text(item.get("description", "")),
                location=item.get("location", ""),
                remote=item.get("remote"),
                posted_at=str(item.get("created_at", "")),
            )
        )
    return jobs


def jobicy(query: str) -> list[dict]:
    url = "https://jobicy.com/api/v2/remote-jobs?count=50&tag=" + urllib.parse.quote(query)
    data = fetch_json(url)
    jobs = []
    for item in (data or {}).get("jobs", []):
        jobs.append(
            make_job(
                source="jobicy",
                company=item.get("companyName", ""),
                title=item.get("jobTitle", ""),
                url=item.get("url", ""),
                description=html_to_text(item.get("jobDescription", "")),
                location=item.get("jobGeo", ""),
                remote=True,
                posted_at=item.get("pubDate", ""),
            )
        )
    return jobs


def adzuna(app_id: str, app_key: str, country: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 50,
            "what": query,
            "content-type": "application/json",
        }
    )
    data = fetch_json(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?{params}"
    )
    jobs = []
    for item in (data or {}).get("results", []):
        jobs.append(
            make_job(
                source="adzuna",
                company=(item.get("company") or {}).get("display_name", ""),
                title=item.get("title", ""),
                url=item.get("redirect_url", ""),
                description=html_to_text(item.get("description", "")),
                location=(item.get("location") or {}).get("display_name", ""),
                posted_at=item.get("created", ""),
            )
        )
    return jobs
