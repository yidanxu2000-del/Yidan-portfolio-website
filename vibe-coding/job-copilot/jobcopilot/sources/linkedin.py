"""Two ways to get LinkedIn roles in, both of which keep you inside the rules.

1. `from_alert_emails` — you create job alerts on LinkedIn, LinkedIn emails you,
   and this reads those emails out of your own mailbox over IMAP. Nothing touches
   LinkedIn's servers. This is the recommended path.

2. `from_assisted_search` — drives a real browser you are already logged into,
   reads the search results you can see, and stops there. It never applies to
   anything. Automated access to LinkedIn is against their User Agreement and can
   get an account restricted, so it is off unless you switch it on yourself.

Alert emails carry the title, company and link but not the job description, so
those postings arrive flagged `needs_detail` — paste the description in from the
job page before analysing.
"""

from __future__ import annotations

import email
import email.utils
import imaplib
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from .base import SourceError, make_job

JOB_LINK = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)")


class _AlertParser(HTMLParser):
    """Pulls (job id, title, trailing text) triples out of a LinkedIn alert email."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hits: list[dict] = []
        self._current: dict | None = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag != "a":
            if self._current is not None:
                self._depth += 1
            return
        href = dict(attrs).get("href", "") or ""
        match = JOB_LINK.search(href)
        if match:
            self._flush()
            self._current = {"job_id": match.group(1), "title": "", "tail": ""}
            self._depth = 0
        else:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current is not None and self._depth == 0:
            self._current["_closed"] = True
        elif self._current is not None and self._depth > 0:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._current.get("_closed"):
            self._current["tail"] += " " + text
        else:
            self._current["title"] += " " + text

    def _flush(self) -> None:
        if self._current and self._current["title"].strip():
            self.hits.append(self._current)
        self._current = None

    def close(self) -> None:  # noqa: A003
        super().close()
        self._flush()


def _split_tail(tail: str) -> tuple[str, str]:
    """LinkedIn writes 'Company · Location' after the title. Sometimes it doesn't."""
    tail = " ".join(tail.split())
    for sep in ("·", "•", "|", " - "):
        if sep in tail:
            left, _, right = tail.partition(sep)
            return left.strip(), right.strip()[:120]
    return tail[:80].strip(), ""


def _bodies(message: email.message.Message) -> list[str]:
    out = []
    for part in message.walk():
        if part.get_content_type() in ("text/html", "text/plain"):
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset() or "utf-8"
                out.append(payload.decode(charset, errors="replace"))
    return out


def from_alert_emails(cfg) -> list[dict]:
    """Read LinkedIn job-alert emails from your own IMAP mailbox."""
    li = cfg.linkedin
    if not (li.imap_user and li.imap_password):
        raise SourceError("linkedin.imap_user and JOBCOPILOT_IMAP_PASSWORD are required")

    since = (datetime.now(timezone.utc) - timedelta(days=li.lookback_days)).strftime(
        "%d-%b-%Y"
    )
    jobs: dict[str, dict] = {}
    try:
        with imaplib.IMAP4_SSL(li.imap_host, li.imap_port) as imap:
            imap.login(li.imap_user, li.imap_password)
            imap.select(li.imap_folder, readonly=True)
            status, data = imap.search(
                None, "SINCE", since, "FROM", "linkedin.com"
            )
            if status != "OK":
                raise SourceError(f"IMAP search failed: {status}")
            ids = (data[0] or b"").split()
            for msg_id in ids[-200:]:
                status, payload = imap.fetch(msg_id, "(RFC822)")
                if status != "OK" or not payload or not payload[0]:
                    continue
                message = email.message_from_bytes(payload[0][1])
                received = ""
                if message.get("Date"):
                    try:
                        received = email.utils.parsedate_to_datetime(
                            message["Date"]
                        ).isoformat()
                    except (TypeError, ValueError):
                        received = ""
                for body in _bodies(message):
                    parser = _AlertParser()
                    try:
                        parser.feed(body)
                        parser.close()
                    except Exception:
                        continue
                    for hit in parser.hits:
                        company, location = _split_tail(hit["tail"])
                        url = f"https://www.linkedin.com/jobs/view/{hit['job_id']}/"
                        job = make_job(
                            source="linkedin:alert",
                            company=company,
                            title=" ".join(hit["title"].split()),
                            url=url,
                            description="",
                            location=location,
                            posted_at=received,
                            extra={
                                "needs_detail": True,
                                "linkedin_job_id": hit["job_id"],
                            },
                        )
                        jobs[job["id"]] = job
    except imaplib.IMAP4.error as exc:
        raise SourceError(
            f"IMAP login or fetch failed ({exc}). For outlook.com with 2FA you need "
            "an app password, not your account password."
        ) from exc

    return list(jobs.values())


def from_assisted_search(cfg) -> list[dict]:
    """Read search results in a browser you are already signed into.

    Requires `pip install playwright`. Chromium is expected to be installed
    already. Read-only: it opens search pages, reads the cards, and closes.
    """
    li = cfg.linkedin
    if not li.assisted_enabled:
        raise SourceError("linkedin.assisted_enabled is false")
    if not li.assisted_searches:
        raise SourceError("linkedin.assisted_searches is empty")
    if not li.browser_profile_dir:
        raise SourceError(
            "linkedin.browser_profile_dir is required — point it at a directory to "
            "hold a persistent browser profile, then sign in once when it opens."
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SourceError("pip install playwright") from exc

    jobs: dict[str, dict] = {}
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            li.browser_profile_dir, headless=False
        )
        page = context.new_page()
        try:
            for search_url in li.assisted_searches:
                page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_timeout(4_000)
                cards = page.locator("a[href*='/jobs/view/']")
                for i in range(min(cards.count(), li.assisted_max_results)):
                    card = cards.nth(i)
                    href = card.get_attribute("href") or ""
                    match = JOB_LINK.search(href)
                    if not match:
                        continue
                    title = " ".join((card.inner_text() or "").split())
                    if not title:
                        continue
                    job = make_job(
                        source="linkedin:assisted",
                        company="",
                        title=title,
                        url=f"https://www.linkedin.com/jobs/view/{match.group(1)}/",
                        description="",
                        extra={
                            "needs_detail": True,
                            "linkedin_job_id": match.group(1),
                        },
                    )
                    jobs[job["id"]] = job
                # Deliberately unhurried — this is a human-paced read, not a crawl.
                page.wait_for_timeout(3_000)
        finally:
            context.close()
    return list(jobs.values())
