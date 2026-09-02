"""Manual entry: paste a description, or hand over a URL and let it fetch.

The escape hatch that makes everything else optional. Anything the automated
sources can't reach — a LinkedIn posting, a careers page on a bespoke CMS, a role
someone emailed you — comes in through here.
"""

from __future__ import annotations

import re

from .base import fetch_text, html_to_text, make_job

_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_OG = re.compile(
    r"<meta[^>]+property=[\"']og:(title|site_name)[\"'][^>]+content=[\"'](.*?)[\"']",
    re.I,
)


def from_paste(
    *,
    title: str,
    company: str,
    description: str,
    url: str = "",
    location: str = "",
    apply_email: str = "",
) -> dict:
    if not description.strip():
        raise ValueError("A description is required — that's what gets analysed.")
    return make_job(
        source="manual",
        company=company,
        title=title or "Untitled role",
        url=url,
        description=description,
        location=location,
        apply_email=apply_email,
    )


def from_url(url: str) -> dict:
    """Fetch a public job page and pull the readable text out of it.

    Plenty of boards render postings in JavaScript or block unauthenticated
    requests. When that happens the text comes back thin or empty — paste the
    description in instead rather than analysing a shell.
    """
    html = fetch_text(url)
    og = {key.lower(): value for key, value in _OG.findall(html)}
    title = og.get("title", "")
    if not title:
        match = _TITLE.search(html)
        title = html_to_text(match.group(1)) if match else ""

    body = html_to_text(html)
    # Drop nav and cookie-banner chrome by keeping the longest run of prose.
    blocks = [b.strip() for b in body.split("\n\n") if len(b.strip()) > 120]
    description = "\n\n".join(blocks) if blocks else body

    job = make_job(
        source="url",
        company=og.get("site_name", ""),
        title=title or url,
        url=url,
        description=description,
    )
    if len(description) < 400:
        job["extra"]["needs_detail"] = True
        job["extra"]["fetch_note"] = (
            "Only a little text came back — the page probably renders in JavaScript. "
            "Paste the description in by hand."
        )
    return job
