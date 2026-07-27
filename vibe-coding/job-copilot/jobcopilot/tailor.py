"""Resume tailoring: reorder and rephrase the bullet bank for one posting.

The hard rule is that every bullet must cite the bank entry it came from. That
citation is what keeps the output a rewrite rather than a fabrication — you can
check any line against the source in one step.
"""

from __future__ import annotations

from .llm import Claude
from .profile import evidence_digest
from .schemas import TailoredResume

SYSTEM = """\
You tailor one candidate's resume to one job posting.

Absolute rule: every bullet you write must be a rephrasing of a bullet in the \
bank, and you must put that bullet's id in the `source` field. You may compress, \
reorder, re-emphasise and change wording to match the posting's language. You may \
not add a fact, a metric, a technology, a company or an outcome that is not \
already in the bank. If the posting wants something the candidate lacks, leave it \
out and note it in `omitted` — do not invent an approximation.

Choose which roles appear and in what order. A posting for a design systems role \
should lead with the Xiaomi Auto system UI work; an AI product role should lead \
with 1Soul. Drop roles that add nothing rather than padding.

Use the posting's own vocabulary where the candidate genuinely has the \
experience — that is what gets through keyword screens. Do not keyword-stuff.

Keep bullets to one line each where possible. Strong verb first, outcome where \
the bank gives you one.
"""

PROMPT = """\
CANDIDATE PROFILE (bullet ids are in parentheses — cite them)
============================================================
{profile}

THE ANALYSIS OF THIS POSTING
============================
Angle to take: {angle}
Keywords that matter: {keywords}
Requirements assessed: {must_haves}

JOB POSTING
===========
{company} — {title}
{location}

{description}

Produce the tailored resume.
"""


def tailor_resume(job: dict, profile: dict, analysis: dict, claude: Claude) -> dict:
    if not claude.available:
        # Without a model, hand back the full bank in its natural order. It's a
        # valid resume, just not tailored — and it's honest about that.
        return {
            "engine": "none",
            "headline": profile.get("headline", ""),
            "summary": profile.get("summary", ""),
            "roles": [
                {
                    "company": role["company"],
                    "role": role["role"],
                    "dates": role["dates"],
                    "bullets": [
                        {"source": f"{role['id']}.{i}", "text": b["text"]}
                        for i, b in enumerate(role.get("bullets", []))
                    ],
                }
                for role in profile.get("experience", [])
            ],
            "skills": [
                skill
                for group in (profile.get("skills") or {}).values()
                for skill in group
            ],
            "keyword_coverage": [],
            "omitted": ["Not tailored — no ANTHROPIC_API_KEY set."],
        }

    must_haves = "; ".join(
        f"{r.get('requirement', '')} [{r.get('status', '')}]"
        for r in analysis.get("must_haves", [])
    )
    result: TailoredResume = claude.structured(
        TailoredResume,
        SYSTEM,
        PROMPT.format(
            profile=evidence_digest(profile),
            angle=analysis.get("angle", ""),
            keywords=", ".join(analysis.get("keywords", [])),
            must_haves=must_haves,
            company=job.get("company", ""),
            title=job.get("title", ""),
            location=job.get("location", ""),
            description=(job.get("description") or "")[:20_000],
        ),
    )
    payload = {"engine": "claude", **result.model_dump()}
    payload["unsourced"] = _unsourced_bullets(payload, profile)
    return payload


def _unsourced_bullets(resume: dict, profile: dict) -> list[str]:
    """Flag any bullet whose cited source isn't in the bank.

    A cheap integrity check on the model's own citations — anything listed here
    should be read before it goes out.
    """
    valid = {
        f"{role['id']}.{i}"
        for role in profile.get("experience", [])
        for i in range(len(role.get("bullets", [])))
    }
    return [
        bullet.get("text", "")
        for role in resume.get("roles", [])
        for bullet in role.get("bullets", [])
        if bullet.get("source") not in valid
    ]
