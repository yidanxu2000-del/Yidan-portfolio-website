"""Job analysis: is this worth applying to, and if so, on what grounds."""

from __future__ import annotations

import re

from .llm import Claude
from .profile import evidence_digest
from .schemas import JobAnalysis

SYSTEM = """\
You assess job postings for one specific candidate and you are hard to impress.

The candidate profile below is the ONLY source of fact about them. Never credit \
them with experience it does not contain. If a posting requires something they \
lack, that is a gap — say so plainly.

Score honestly. A score above 80 means they are a genuinely strong candidate and \
would likely get a first conversation. 40 to 65 means a real stretch. Below 40 \
means don't bother. Most postings are not above 80; a distribution where \
everything scores well is a broken one.

Two things carry disproportionate weight because they waste the most time when \
missed: seniority mismatch (a posting wanting 8+ years is not a fit for a \
mid-level candidate, however good the work), and right-to-work restrictions. \
Read the posting for both and report what it actually says.

For lead_projects, use only the project slugs given in the profile.
"""

PROMPT = """\
CANDIDATE PROFILE
=================
{profile}

TARGET ROLES: {target_roles}
TARGET LOCATIONS: {target_locations}
NOT INTERESTED IN: {avoid}

JOB POSTING
===========
Company: {company}
Title: {title}
Location: {location}
Source: {source}
URL: {url}

{description}

Assess the fit.
"""

# Rough keyword scoring, used when no API key is set so the tool still sorts a
# sweep into something readable. It is a triage aid, not an assessment.
_STOP = {
    "and", "the", "for", "with", "you", "our", "are", "will", "have", "this",
    "that", "from", "your", "who", "all", "can", "not", "but", "has", "was",
    "role", "team", "work", "working", "job", "about", "they", "them", "their",
    "also", "any", "another", "been", "both", "each", "either", "every", "few",
    "how", "into", "its", "least", "like", "looking", "many", "may", "might",
    "more", "most", "much", "must", "need", "needs", "nice", "own", "per",
    "should", "some", "such", "than", "then", "there", "these", "those",
    "through", "very", "want", "well", "what", "when", "where", "which",
    "while", "why", "would", "years", "year", "plus", "etc", "including",
    "able", "across", "along", "already", "always", "level", "new", "get",
    "help", "make", "take", "use", "using", "join", "join us", "one", "two",
}


def _tokens(text: str) -> set[str]:
    """Words worth comparing. Trailing punctuation stripped so 'engineers.' isn't a term."""
    words = set()
    for raw in re.findall(r"[a-z][a-z+#/.\-]{2,}", (text or "").lower()):
        word = raw.strip(".-/")
        if len(word) >= 3 and word not in _STOP:
            words.add(word)
    return words


"""Deterministic scans for the two things that waste the most time when missed."""

# Written as patterns rather than literal phrases because postings say this a
# dozen different ways: "unable to provide visa sponsorship", "cannot sponsor",
# "must have existing right to work".
_NO_SPONSOR = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:un(?:able|available)|not able|cannot|can'?t|do(?:es)? not|don'?t|won'?t)\b[^.]{0,40}\bsponsor",
        r"\bno\b[^.]{0,20}\bsponsorship\b",
        r"\bsponsorship\b[^.]{0,30}\bnot\b[^.]{0,20}\b(?:available|provided|offered|possible)\b",
        r"\bwithout\b[^.]{0,20}\bsponsorship\b",
        r"\bmust\b[^.]{0,40}\bright to work\b",
        r"\bmust be\b[^.]{0,30}\b(?:authori[sz]ed|eligible|permitted)\b[^.]{0,20}\bto work\b",
        r"\b(?:requires?|must (?:have|hold))\b[^.]{0,30}\b(?:security|government)\s+clearance\b",
        r"\bcitizens?(?:hip)?\b[^.]{0,25}\b(?:required|only)\b",
    )
]
_SPONSORS = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:visa\s+)?sponsorship\b[^.]{0,25}\b(?:available|provided|offered)\b",
        r"\bwe\b[^.]{0,20}\b(?:can|do|will|happy to|able to)\b[^.]{0,15}\bsponsor",
        r"\bsponsor(?:ship)?\b[^.]{0,20}\b(?:eligible|licence|license)\b",
        r"\bskilled worker visa\b",
    )
]
_YEARS = re.compile(r"(\d{1,2})\s*(?:\+|or more|plus)?\s*(?:-|to|–)?\s*(\d{1,2})?\s*\+?\s*years?", re.I)


def _sentence_around(text: str, match: re.Match) -> str:
    """The sentence a match landed in, so the evidence is quotable.

    Breaks on sentence punctuation and blank lines only. A single newline is a
    soft wrap in most postings, and treating it as a boundary cuts the quote
    mid-clause ("...you must have existing").
    """
    starts = [text.rfind(sep, 0, match.start()) for sep in (". ", ".\n", "\n\n", "• ", "- ")]
    start = max(starts) + 1 if max(starts) >= 0 else 0
    ends = [
        i
        for i in (text.find(sep, match.end()) for sep in (". ", ".\n", "\n\n"))
        if i != -1
    ]
    end = min(ends) + 1 if ends else len(text)
    return " ".join(text[start:end].split())[:240].lstrip(". ")


def scan_work_authorisation(description: str) -> dict:
    """Surface right-to-work language. Restrictions win over offers.

    Reports 'restricted', not 'excludes' — whether a restriction actually blocks
    you depends on your status, which a regex can't know. A role requiring UK
    right to work is fine for someone who has it; the same sentence about the US
    is not. The scan's job is to make sure you see the sentence.
    """
    text = description or ""
    for pattern in _NO_SPONSOR:
        match = pattern.search(text)
        if match:
            return {"stance": "restricted", "evidence": _sentence_around(text, match)}
    for pattern in _SPONSORS:
        match = pattern.search(text)
        if match:
            return {"stance": "sponsors", "evidence": _sentence_around(text, match)}
    return {"stance": "silent", "evidence": "not mentioned"}


def _candidate_max_years(profile: dict) -> int:
    """Years of experience claimed in the seniority line, or a sane default.

    Only counts numbers attached to 'year' — a line like 'two 0-to-1 roles' would
    otherwise contribute a stray figure and skew the comparison.
    """
    seniority = profile.get("seniority", "")
    years = [int(m.group(1)) for m in _YEARS.finditer(seniority)]
    years += [int(m.group(2)) for m in _YEARS.finditer(seniority) if m.group(2)]
    return max(years) if years else 5


def scan_years_required(description: str, profile: dict) -> tuple[int, str]:
    """The highest minimum-years figure the posting asks for, if it's a stretch."""
    ceiling = _candidate_max_years(profile)
    worst, evidence = 0, ""
    for match in _YEARS.finditer(description or ""):
        low = int(match.group(1))
        # In "5-8 years" the lower bound is the requirement.
        if low > worst:
            worst, evidence = low, _sentence_around(description, match)
    if worst > ceiling + 1:
        return worst, evidence
    return 0, ""


def heuristic_analysis(job: dict, profile: dict) -> dict:
    """Keyword overlap between posting and profile. Cheap, blunt, better than nothing."""
    profile_text = " ".join(
        [
            profile.get("summary", ""),
            profile.get("headline", ""),
            " ".join(" ".join(v) for v in (profile.get("skills") or {}).values()),
            " ".join(
                bullet["text"]
                for role in profile.get("experience", [])
                for bullet in role.get("bullets", [])
            ),
            " ".join(p.get("pitch", "") for p in profile.get("projects", [])),
        ]
    )
    profile_words = _tokens(profile_text)
    job_words = _tokens(f"{job.get('title', '')} {job.get('description', '')}")
    if not job_words:
        overlap, missing, score = set(), [], 0
    else:
        overlap = profile_words & job_words
        missing = sorted(job_words - profile_words)[:20]
        score = min(95, round(100 * len(overlap) / max(len(job_words), 1) * 2.2))

    title = (job.get("title") or "").lower()
    if any(
        role.split()[0].lower() in title
        for role in profile.get("target_roles", [])
        if role
    ):
        score += 8

    description = job.get("description") or ""
    risks: list[str] = []

    work_auth = scan_work_authorisation(description)
    if work_auth["stance"] == "restricted":
        risks.append(f"Right to work — check this against your status: {work_auth['evidence']}")
        score -= 8

    years, years_evidence = scan_years_required(description, profile)
    if years:
        risks.append(
            f"Asks for {years}+ years against your {profile.get('seniority', 'level')}: "
            f"{years_evidence}"
        )
        score -= 14

    # Capped below the range a real assessment uses, so a keyword score never
    # reads as a confident verdict.
    score = max(0, min(72, score))

    return {
        "engine": "keyword",
        "fit_score": score,
        "verdict": "possible" if score >= 45 else "weak",
        "one_line": (
            f"Keyword overlap only ({len(overlap)} shared terms), capped at 72. "
            "Set ANTHROPIC_API_KEY for a real assessment."
        ),
        "role_family": "",
        "seniority": f"posting asks for {years}+ years" if years else "",
        "work_authorisation": work_auth,
        "must_haves": [],
        "keywords": sorted(overlap)[:25],
        "keywords_missing": missing,
        "lead_projects": [],
        "angle": "",
        "risks": risks,
        "questions_to_ask": [],
    }


def analyse(job: dict, profile: dict, claude: Claude) -> dict:
    """Full assessment via Claude, or keyword triage if there's no key."""
    if not (job.get("description") or "").strip():
        return {
            "engine": "none",
            "fit_score": 0,
            "verdict": "skip",
            "one_line": "No job description yet — paste it in, then analyse.",
            "role_family": "",
            "seniority": "",
            "work_authorisation": {"stance": "unclear", "evidence": "no description"},
            "must_haves": [],
            "keywords": [],
            "keywords_missing": [],
            "lead_projects": [],
            "angle": "",
            "risks": ["Description missing."],
            "questions_to_ask": [],
        }

    if not claude.available:
        return heuristic_analysis(job, profile)

    result: JobAnalysis = claude.structured(
        JobAnalysis,
        SYSTEM,
        PROMPT.format(
            profile=evidence_digest(profile),
            target_roles=", ".join(profile.get("target_roles", [])),
            target_locations=", ".join(profile.get("target_locations", [])),
            avoid="; ".join(profile.get("avoid", [])),
            company=job.get("company", ""),
            title=job.get("title", ""),
            location=job.get("location", ""),
            source=job.get("source", ""),
            url=job.get("url", ""),
            # Long postings are mostly boilerplate past this point.
            description=(job.get("description") or "")[:24_000],
        ),
    )
    return _reconcile(job, profile, {"engine": "claude", **result.model_dump()})


def _reconcile(job: dict, profile: dict, analysis: dict) -> dict:
    """Make sure the deterministic findings reach you, whatever the model said.

    The model decides the stance — it has the candidate's stated status and can
    tell a satisfiable requirement from a blocking one. What the scan guarantees
    is that the sentence is never silently dropped: if the posting restricts
    right to work and the model didn't mention it, it gets added to the risks.
    """
    description = job.get("description") or ""

    scanned = scan_work_authorisation(description)
    stated = (analysis.get("work_authorisation") or {}).get("stance")
    if scanned["stance"] == "restricted" and stated in ("silent", None, ""):
        analysis["work_authorisation"] = scanned
        analysis.setdefault("risks", []).insert(
            0, f"Right to work — found in the posting: {scanned['evidence']}"
        )

    years, evidence = scan_years_required(description, profile)
    if years:
        note = f"Asks for {years}+ years against your {profile.get('seniority', 'level')}"
        if not any("years" in risk.lower() for risk in analysis.get("risks", [])):
            analysis.setdefault("risks", []).append(f"{note}: {evidence}")

    analysis["fit_score"] = max(0, min(100, int(analysis.get("fit_score", 0))))
    return analysis
