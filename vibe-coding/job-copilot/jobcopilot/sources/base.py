"""Shared plumbing for job sources: fetching, HTML stripping, stable ids."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "job-copilot/1.0 (personal job search tool)"
TIMEOUT = 25

_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "tr", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
}


class _TextExtractor(HTMLParser):
    """Turns a job description's HTML into readable plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r" *\n *", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed markup shouldn't lose the posting — fall back to tag stripping.
        return re.sub(r"<[^>]+>", " ", html).strip()
    return parser.text()


def fetch_json(url: str, headers: dict | None = None) -> object:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_text(url: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def canonical_url(url: str) -> str:
    """Strip tracking params so the same posting gets the same id every run."""
    if not url:
        return ""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    keep = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query)
        if not k.lower().startswith(("utm_", "gh_", "trk", "ref"))
        and k.lower() not in ("source", "src", "trackingid", "refid")
    ]
    return urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urllib.parse.urlencode(keep),
            "",
        )
    )


def make_job(
    *,
    source: str,
    company: str,
    title: str,
    url: str,
    description: str,
    location: str = "",
    posted_at: str = "",
    remote: bool | None = None,
    apply_email: str = "",
    extra: dict | None = None,
) -> dict:
    url = canonical_url(url)
    # Id off the URL where there is one, otherwise off company+title, so a
    # posting without a stable link still dedupes across runs.
    basis = url or f"{source}:{company}:{title}"
    return {
        "id": hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16],
        "source": source,
        "company": (company or "").strip(),
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "remote": remote,
        "url": url,
        "description": (description or "").strip(),
        "posted_at": posted_at,
        "apply_email": apply_email,
        "extra": extra or {},
    }


class SourceError(RuntimeError):
    """A single source failed. Collected and reported; never fatal to a run."""


def safe_collect(name: str, fn, *args, **kwargs) -> tuple[list[dict], str | None]:
    """Run a source, returning (jobs, error). One bad board can't kill the sweep."""
    try:
        return list(fn(*args, **kwargs)), None
    except urllib.error.HTTPError as exc:
        return [], f"{name}: HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return [], f"{name}: {exc.reason}"
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return [], f"{name}: unexpected response ({exc})"
    except SourceError as exc:
        return [], f"{name}: {exc}"
