"""Company job boards, read through each ATS's own public JSON API.

These are documented, keyless, and meant to be read by machines — which is why
they're the backbone of discovery here rather than scraping search pages.

To add a company, find its board token in the careers-page URL:
  boards.greenhouse.io/TOKEN            -> greenhouse
  jobs.lever.co/TOKEN                   -> lever
  jobs.ashbyhq.com/TOKEN                -> ashby
  apply.workable.com/TOKEN              -> workable
  jobs.smartrecruiters.com/TOKEN        -> smartrecruiters
  TOKEN.recruitee.com                   -> recruitee
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .base import fetch_json, html_to_text, make_job


def greenhouse(token: str) -> list[dict]:
    data = fetch_json(
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    )
    jobs = []
    for item in (data or {}).get("jobs", []):
        offices = item.get("offices") or []
        location = (item.get("location") or {}).get("name") or ", ".join(
            o.get("name", "") for o in offices
        )
        jobs.append(
            make_job(
                source=f"greenhouse:{token}",
                company=token,
                title=item.get("title", ""),
                url=item.get("absolute_url", ""),
                description=html_to_text(item.get("content", "")),
                location=location,
                posted_at=item.get("updated_at", ""),
            )
        )
    return jobs


def lever(token: str) -> list[dict]:
    data = fetch_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
    jobs = []
    for item in data or []:
        cats = item.get("categories") or {}
        body = item.get("descriptionPlain") or html_to_text(item.get("description", ""))
        lists = "\n\n".join(
            f"{blk.get('text', '')}\n{html_to_text(blk.get('content', ''))}"
            for blk in item.get("lists", [])
        )
        jobs.append(
            make_job(
                source=f"lever:{token}",
                company=token,
                title=item.get("text", ""),
                url=item.get("hostedUrl", ""),
                description=f"{body}\n\n{lists}".strip(),
                location=cats.get("location", "") or "",
                remote=(cats.get("commitment", "") or "").lower() == "remote" or None,
            )
        )
    return jobs


def ashby(token: str) -> list[dict]:
    data = fetch_json(
        f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"
    )
    jobs = []
    for item in (data or {}).get("jobs", []):
        jobs.append(
            make_job(
                source=f"ashby:{token}",
                company=token,
                title=item.get("title", ""),
                url=item.get("jobUrl", ""),
                description=item.get("descriptionPlain")
                or html_to_text(item.get("descriptionHtml", "")),
                location=item.get("location", ""),
                remote=item.get("isRemote"),
                posted_at=item.get("publishedAt", ""),
            )
        )
    return jobs


def workable(token: str) -> list[dict]:
    data = fetch_json(
        f"https://apply.workable.com/api/v1/widget/accounts/{token}?details=true"
    )
    company = (data or {}).get("name") or token
    jobs = []
    for item in (data or {}).get("jobs", []):
        description = "\n\n".join(
            html_to_text(item.get(field, ""))
            for field in ("description", "requirements", "benefits")
            if item.get(field)
        )
        jobs.append(
            make_job(
                source=f"workable:{token}",
                company=company,
                title=item.get("title", ""),
                url=item.get("url") or item.get("application_url", ""),
                description=description,
                location=", ".join(
                    p
                    for p in (item.get("city"), item.get("state"), item.get("country"))
                    if p
                ),
                remote=item.get("telecommuting"),
                posted_at=item.get("published_on", ""),
            )
        )
    return jobs


_SR_SECTIONS = (
    "companyDescription",
    "jobDescription",
    "qualifications",
    "additionalInformation",
)


def _smartrecruiters_detail(token: str, posting_id: str) -> str:
    """The list endpoint omits the body, so each posting needs its own call."""
    try:
        detail = fetch_json(
            f"https://api.smartrecruiters.com/v1/companies/{token}/postings/{posting_id}"
        )
    except Exception:
        return ""
    sections = ((detail or {}).get("jobAd") or {}).get("sections") or {}
    return "\n\n".join(
        text
        for key in _SR_SECTIONS
        if (text := html_to_text((sections.get(key) or {}).get("text", "")))
    )


def smartrecruiters(token: str) -> list[dict]:
    data = fetch_json(
        f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100"
    )
    items = (data or {}).get("content", [])
    # One detail call per posting, a few at a time — sequentially this takes
    # half a minute for a large employer.
    with ThreadPoolExecutor(max_workers=6) as pool:
        bodies = list(
            pool.map(lambda i: _smartrecruiters_detail(token, i.get("id", "")), items)
        )

    jobs = []
    for item, description in zip(items, bodies):
        loc = item.get("location") or {}
        job = make_job(
            source=f"smartrecruiters:{token}",
            company=(item.get("company") or {}).get("name") or token,
            title=item.get("name", ""),
            url=item.get("postingUrl")
            or f"https://jobs.smartrecruiters.com/{token}/{item.get('id', '')}",
            description=description,
            location=", ".join(
                p for p in (loc.get("city"), loc.get("region"), loc.get("country")) if p
            ),
            remote=loc.get("remote"),
            posted_at=item.get("releasedDate", ""),
        )
        if not description:
            job["extra"]["needs_detail"] = True
        jobs.append(job)
    return jobs


def recruitee(token: str) -> list[dict]:
    data = fetch_json(f"https://{token}.recruitee.com/api/offers/")
    jobs = []
    for item in (data or {}).get("offers", []):
        jobs.append(
            make_job(
                source=f"recruitee:{token}",
                company=item.get("company_name") or token,
                title=item.get("title", ""),
                url=item.get("careers_url") or item.get("careers_apply_url", ""),
                description=html_to_text(item.get("description", ""))
                + "\n\n"
                + html_to_text(item.get("requirements", "")),
                location=", ".join(
                    p for p in (item.get("city"), item.get("country")) if p
                ),
                remote=item.get("remote"),
                posted_at=item.get("published_at", ""),
            )
        )
    return jobs


PROVIDERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workable": workable,
    "smartrecruiters": smartrecruiters,
    "recruitee": recruitee,
}
