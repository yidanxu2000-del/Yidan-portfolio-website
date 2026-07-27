"""Print-ready HTML for the tailored resume and the letter.

HTML rather than a generated PDF on purpose: you open it, read it, adjust the CSS
if you want to, and print to PDF from the browser. That keeps the last step in
your hands, which for a designer is the right place for it.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from .config import DATA_DIR

OUT_DIR = DATA_DIR / "out"

_PAGE_CSS = """\
:root{
  --ink:#1d1d1f; --muted:#6e6e73; --hair:rgba(0,0,0,.14); --accent:#0080c8;
  --font:-apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Helvetica Neue",Arial,sans-serif;
}
@page{ size:A4; margin:14mm 15mm; }
*{ box-sizing:border-box; }
body{
  margin:0; padding:24px; background:#f5f5f7; color:var(--ink);
  font-family:var(--font); font-size:10.5pt; line-height:1.45;
  -webkit-font-smoothing:antialiased;
}
.sheet{
  max-width:210mm; margin:0 auto; background:#fff; padding:16mm 15mm;
  box-shadow:0 1px 3px rgba(0,0,0,.08),0 12px 40px rgba(0,0,0,.06);
}
h1{ margin:0; font-size:23pt; letter-spacing:-.02em; line-height:1.05; }
.headline{ margin:3px 0 0; color:var(--accent); font-size:11pt; font-weight:500; }
.contact{ margin:8px 0 0; color:var(--muted); font-size:9pt; }
.contact a{ color:var(--muted); text-decoration:none; }
.summary{ margin:14px 0 0; font-size:10.5pt; }
h2{
  margin:20px 0 8px; padding-bottom:4px; border-bottom:1px solid var(--hair);
  font-size:9pt; font-weight:600; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted);
}
.role{ margin:0 0 12px; break-inside:avoid; }
.role__head{ display:flex; justify-content:space-between; gap:12px; align-items:baseline; }
.role__title{ font-weight:600; font-size:10.5pt; }
.role__dates{ color:var(--muted); font-size:9pt; white-space:nowrap; }
.role__company{ color:var(--muted); font-size:9.5pt; margin:1px 0 5px; }
ul{ margin:0; padding-left:16px; }
li{ margin:0 0 3px; }
.tags{ display:flex; flex-wrap:wrap; gap:5px; }
.tag{
  border:1px solid var(--hair); border-radius:980px; padding:2px 9px;
  font-size:8.5pt; color:var(--muted);
}
.edu{ display:flex; justify-content:space-between; gap:12px; margin:0 0 4px; }
.edu__dates{ color:var(--muted); font-size:9pt; white-space:nowrap; }
.letter p{ margin:0 0 11px; }
.letter a{ color:var(--accent); }
.meta{
  max-width:210mm; margin:0 auto 12px; color:var(--muted); font-size:9pt;
}
.meta code{ font-family:"SF Mono",Menlo,monospace; }
@media print{
  body{ background:#fff; padding:0; }
  .sheet{ box-shadow:none; padding:0; max-width:none; }
  .meta{ display:none; }
}
"""


def _esc(value) -> str:
    return html.escape(str(value or ""))


def _inline_markdown(text: str) -> str:
    """Links, bold and italic. Deliberately not a full Markdown implementation."""
    out = _esc(text)
    out = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2">\1</a>',
        out,
    )
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", out)
    return out


def markdown_to_paragraphs(text: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text or "") if b.strip()]
    return "\n".join(
        f"<p>{_inline_markdown(b).replace(chr(10), '<br>')}</p>" for b in blocks
    )


def _shell(title: str, note: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title>
<style>{_PAGE_CSS}</style>
</head><body>
<div class="meta">{note} — print to PDF with <code>Cmd/Ctrl+P</code>.</div>
<div class="sheet">{body}</div>
</body></html>"""


def render_resume(profile: dict, resume: dict, job: dict) -> str:
    contact_bits = [
        _esc(profile.get("location")),
        _esc(profile.get("phone")),
        f'<a href="mailto:{_esc(profile.get("email"))}">{_esc(profile.get("email"))}</a>',
        f'<a href="{_esc(profile.get("portfolio"))}">{_esc(profile.get("portfolio", "")).replace("https://", "")}</a>',
        f'<a href="{_esc(profile.get("linkedin"))}">LinkedIn</a>',
    ]
    parts = [
        f'<h1>{_esc(profile.get("name"))}</h1>',
        f'<p class="headline">{_esc(resume.get("headline") or profile.get("headline"))}</p>',
        f'<p class="contact">{" &nbsp;·&nbsp; ".join(b for b in contact_bits if b)}</p>',
        f'<p class="summary">{_esc(resume.get("summary") or profile.get("summary"))}</p>',
    ]

    if resume.get("roles"):
        parts.append("<h2>Experience</h2>")
        for role in resume["roles"]:
            bullets = "".join(
                f"<li>{_esc(b.get('text'))}</li>" for b in role.get("bullets", [])
            )
            parts.append(
                '<div class="role">'
                '<div class="role__head">'
                f'<span class="role__title">{_esc(role.get("role"))}</span>'
                f'<span class="role__dates">{_esc(role.get("dates"))}</span>'
                "</div>"
                f'<div class="role__company">{_esc(role.get("company"))}</div>'
                f"<ul>{bullets}</ul></div>"
            )

    if resume.get("skills"):
        tags = "".join(f'<span class="tag">{_esc(s)}</span>' for s in resume["skills"])
        parts.append(f'<h2>Skills</h2><div class="tags">{tags}</div>')

    if profile.get("education"):
        parts.append("<h2>Education</h2>")
        for ed in profile["education"]:
            parts.append(
                '<div class="edu"><span>'
                f'<strong>{_esc(ed.get("school"))}</strong> — {_esc(ed.get("degree"))}'
                f'</span><span class="edu__dates">{_esc(ed.get("dates"))}</span></div>'
            )

    if profile.get("awards"):
        parts.append(
            "<h2>Awards</h2><ul>"
            + "".join(f"<li>{_esc(a)}</li>" for a in profile["awards"])
            + "</ul>"
        )

    note = f'Tailored for {_esc(job.get("title"))} at {_esc(job.get("company"))}'
    return _shell(
        f'{profile.get("name", "Resume")} — {job.get("company", "")}', note, "".join(parts)
    )


def render_letter(profile: dict, letter: dict, job: dict) -> str:
    header = (
        f'<h1>{_esc(profile.get("name"))}</h1>'
        f'<p class="contact">{_esc(profile.get("location"))} &nbsp;·&nbsp; '
        f'<a href="mailto:{_esc(profile.get("email"))}">{_esc(profile.get("email"))}</a>'
        f' &nbsp;·&nbsp; <a href="{_esc(profile.get("portfolio"))}">'
        f'{_esc(profile.get("portfolio", "")).replace("https://", "")}</a></p>'
        f'<h2>{_esc(job.get("title"))} — {_esc(job.get("company"))}</h2>'
    )
    body = f'<div class="letter">{markdown_to_paragraphs(letter.get("body", ""))}</div>'
    note = f'Cover letter for {_esc(job.get("company"))}'
    return _shell(f'Cover letter — {job.get("company", "")}', note, header + body)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "role"


def write_documents(profile: dict, job: dict, resume: dict | None, letter: dict | None) -> dict:
    """Write whichever documents exist to data/out/ and return their paths."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f'{_slug(job.get("company"))}-{_slug(job.get("title"))}-{job["id"][:6]}'
    written: dict[str, str] = {}
    if resume:
        path = OUT_DIR / f"{stem}-resume.html"
        path.write_text(render_resume(profile, resume, job), "utf-8")
        written["resume"] = str(path)
    if letter:
        path = OUT_DIR / f"{stem}-letter.html"
        path.write_text(render_letter(profile, letter, job), "utf-8")
        written["letter"] = str(path)
    return written


def relative_out(path: str) -> str:
    """A path the local server can serve, for the preview links in the UI."""
    try:
        return str(Path(path).relative_to(DATA_DIR)).replace("\\", "/")
    except ValueError:
        return ""
