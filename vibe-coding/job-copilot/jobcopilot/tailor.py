"""Resume tailoring: reorder and rephrase the bullet bank for one posting.

The hard rule is that every bullet must cite the bank entry it came from. That
citation is what keeps the output a rewrite rather than a fabrication — you can
check any line against the source in one step.
"""

from __future__ import annotations

from .lexicon import tokens
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


def heuristic_tailor(job: dict, profile: dict) -> dict:
    """Select and reorder real bullets by keyword match. Nothing is rewritten.

    Every word here is copied verbatim from the bank, so there is zero
    fabrication risk — the only judgment this makes is which of your own true
    statements to put first and which to leave off. Rephrasing to match the
    posting's language is what the model does; this only picks and orders.
    """
    description = job.get("description") or ""
    job_words = tokens(f"{job.get('title', '')} {description}")

    scored_roles = []
    for role in profile.get("experience", []):
        bullet_scores = []
        for i, bullet in enumerate(role.get("bullets", [])):
            bwords = tokens(bullet.get("text", "") + " " + " ".join(bullet.get("tags", [])))
            bullet_scores.append((len(job_words & bwords), i, bullet))
        kept = sorted((b for b in bullet_scores if b[0] > 0), key=lambda b: (-b[0], b[1]))
        if kept:
            scored_roles.append((sum(s for s, _, _ in kept), role, kept))
    scored_roles.sort(key=lambda r: -r[0])

    if scored_roles:
        roles_out = [
            {
                "company": role["company"],
                "role": role["role"],
                "dates": role["dates"],
                "bullets": [
                    {"source": f"{role['id']}.{i}", "text": bullet["text"]}
                    for _, i, bullet in sorted(kept, key=lambda b: b[1])
                ],
            }
            for _, role, kept in scored_roles
        ]
        matched_ids = {role["id"] for _, role, _ in scored_roles}
        omitted = [
            f"{role['role']} at {role['company']} — nothing in it matched this posting's wording"
            for role in profile.get("experience", [])
            if role["id"] not in matched_ids
        ]
    else:
        # Nothing matched well enough to select from — show everything rather
        # than an empty resume, and say plainly why.
        roles_out = [
            {
                "company": role["company"],
                "role": role["role"],
                "dates": role["dates"],
                "bullets": [
                    {"source": f"{role['id']}.{i}", "text": bullet["text"]}
                    for i, bullet in enumerate(role.get("bullets", []))
                ],
            }
            for role in profile.get("experience", [])
        ]
        omitted = [
            "Nothing in the posting matched well enough to select from, so nothing "
            "was left out — this is your full bank."
        ]

    all_skills = [s for group in profile.get("skills", {}).values() for s in group]
    matched = [s for s in all_skills if tokens(s) & job_words]
    rest = [s for s in all_skills if s not in matched]

    return {
        "engine": "keyword",
        "headline": profile.get("headline", ""),
        "summary": profile.get("summary", ""),
        "roles": roles_out,
        "skills": matched + rest,
        "keyword_coverage": sorted(job_words & {t for s in all_skills for t in tokens(s)}),
        "omitted": omitted,
    }


def tailor_resume(job: dict, profile: dict, analysis: dict, claude: Claude) -> dict:
    if not claude.available:
        payload = heuristic_tailor(job, profile)
        payload["unsourced"] = _unsourced_bullets(payload, profile)
        return payload

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
