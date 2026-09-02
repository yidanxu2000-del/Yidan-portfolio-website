"""Cover letters: draft one, then edit it by instruction.

Drafting and editing are separate calls on purpose. Editing keeps the current
text as the thing being changed, so you can iterate — 'cut the third paragraph',
'less formal', 'name the Xiaomi regulatory work' — without regenerating from
scratch and losing the version you liked.
"""

from __future__ import annotations

from .llm import Claude
from .profile import evidence_digest
from .schemas import CoverLetter

SYSTEM = """\
You write cover letters for one candidate, in their voice, following the voice \
rules in their profile exactly.

Only use facts from the profile. Every concrete claim should be traceable to a \
bullet or a project in it. Link to at most two project URLs, in Markdown, and only \
where the project genuinely supports the point.

What makes these letters work:
- Open on something specific about this company or role. Not a compliment, not \
  'I was excited to see'. Something that shows you read the posting.
- One piece of evidence per paragraph, told as what happened rather than as a \
  claim about the candidate's qualities.
- Say what they would do in this role. Most letters skip this and it is the part \
  a hiring manager actually reads for.
- Close plainly. No 'I would welcome the opportunity to discuss'.

If no contact name is given, open with 'Hello' rather than inventing a name or \
leaving a placeholder.

Never claim years of experience, tools or domains the profile doesn't show. If \
the posting wants something they lack, either ignore it or address it honestly in \
half a sentence — never bluff.
"""

DRAFT_PROMPT = """\
CANDIDATE PROFILE
=================
{profile}

ANALYSIS OF THIS POSTING
========================
Angle: {angle}
Lead with these projects: {lead_projects}
Their requirements: {must_haves}
Open questions or weak spots: {risks}

JOB POSTING
===========
{company} — {title}
{location}
{url}

{description}

CONTACT: {contact}

Write the letter.
"""

EDIT_SYSTEM = """\
You revise a cover letter on instruction.

Change what was asked and leave everything else alone. Keep the candidate's voice \
and the voice rules from their profile. Never introduce a fact that is not in the \
profile. If an instruction would require inventing something, do the closest \
honest thing and say so in `notes`.
"""

EDIT_PROMPT = """\
CANDIDATE PROFILE (the only permitted source of fact)
====================================================
{profile}

THE POSTING
===========
{company} — {title}

CURRENT LETTER
==============
Subject: {subject}

{body}

INSTRUCTION
===========
{instruction}

Return the revised letter.
"""

_TEMPLATE = """\
Hello,

I'm writing about the {title} role at {company}. I'm a product and UX designer in \
London with dual master's degrees from Imperial College London and the Royal \
College of Art, and two 0-to-1 roles where I owned design end to end.

Most relevant: {project_name} — {project_pitch} ({project_url})

My portfolio is at {portfolio}.

Best,
{name}
"""


def draft_letter(
    job: dict, profile: dict, analysis: dict, claude: Claude, contact: dict | None = None
) -> dict:
    contact = contact or {}
    if not claude.available:
        projects = profile.get("projects") or [{}]
        lead = projects[0]
        return {
            "engine": "none",
            "subject": f"{profile.get('name', '')} — {job.get('title', '')}",
            "body": _TEMPLATE.format(
                title=job.get("title", "the role"),
                company=job.get("company", "your team"),
                project_name=lead.get("name", ""),
                project_pitch=lead.get("pitch", ""),
                project_url=lead.get("url", ""),
                portfolio=profile.get("portfolio", ""),
                name=profile.get("name", ""),
            ),
            "notes": ["Template only — no ANTHROPIC_API_KEY set. Rewrite before sending."],
            "version": 1,
            "history": [],
        }

    contact_line = (
        f"{contact.get('name', '')} <{contact.get('email', '')}>"
        if contact.get("name") or contact.get("email")
        else "no named contact — open with 'Hello'"
    )
    result: CoverLetter = claude.structured(
        CoverLetter,
        SYSTEM,
        DRAFT_PROMPT.format(
            profile=evidence_digest(profile),
            angle=analysis.get("angle", ""),
            lead_projects=", ".join(analysis.get("lead_projects", [])),
            must_haves="; ".join(
                f"{r.get('requirement', '')} [{r.get('status', '')}]"
                for r in analysis.get("must_haves", [])
            ),
            risks="; ".join(analysis.get("risks", [])) or "none noted",
            company=job.get("company", ""),
            title=job.get("title", ""),
            location=job.get("location", ""),
            url=job.get("url", ""),
            description=(job.get("description") or "")[:20_000],
            contact=contact_line,
        ),
    )
    return {"engine": "claude", **result.model_dump(), "version": 1, "history": []}


def edit_letter(
    letter: dict, job: dict, profile: dict, instruction: str, claude: Claude
) -> dict:
    if not claude.available:
        raise RuntimeError("Editing needs ANTHROPIC_API_KEY. Edit the text by hand instead.")
    if not instruction.strip():
        raise ValueError("An instruction is required.")

    result: CoverLetter = claude.structured(
        CoverLetter,
        EDIT_SYSTEM,
        EDIT_PROMPT.format(
            profile=evidence_digest(profile),
            company=job.get("company", ""),
            title=job.get("title", ""),
            subject=letter.get("subject", ""),
            body=letter.get("body", ""),
            instruction=instruction.strip(),
        ),
    )
    # Keep the previous version so an edit is always reversible.
    history = list(letter.get("history", []))
    history.append(
        {
            "version": letter.get("version", 1),
            "subject": letter.get("subject", ""),
            "body": letter.get("body", ""),
            "instruction": instruction.strip(),
        }
    )
    return {
        "engine": "claude",
        **result.model_dump(),
        "version": letter.get("version", 1) + 1,
        "history": history[-10:],
    }
