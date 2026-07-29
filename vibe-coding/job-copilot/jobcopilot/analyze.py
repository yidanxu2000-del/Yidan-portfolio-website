"""Job analysis: is this worth applying to, and if so, on what grounds."""

from __future__ import annotations

import re

from .lexicon import bullet_index, profile_tokens, skill_tokens, tokens
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

# The whole free-mode scorer below is deliberately weighted and transparent — no
# API key needed, and every component is something you could recompute by hand.
# It is still a triage aid, not an assessment: it cannot read intent, tone, or
# anything the posting doesn't say in words. Set ANTHROPIC_API_KEY for that.

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


_LONDON_UK = re.compile(r"\b(london|united kingdom|england|uk)\b", re.I)

# One bullet-list line, however the posting marks it.
_REQ_LINE = re.compile(r"^[ \t]*[-*•‣▪●○][ \t]*(.+?)[ \t]*$", re.M)


def score_role_title(title: str, profile: dict) -> float:
    """0–35. An exact target-role phrase in the title scores full; partial word
    overlap scores proportionally, so 'Design Technologist' still beats 'Designer
    Advocate' without either scoring zero."""
    text = (title or "").lower()
    best = 0.0
    for role in profile.get("target_roles", []):
        role_l = role.lower()
        if role_l in text:
            best = max(best, 35.0)
            continue
        words = [w for w in role_l.split() if len(w) > 2]
        if not words:
            continue
        hits = sum(1 for w in words if w in text)
        best = max(best, 35.0 * hits / len(words) * 0.65)
    return best


def score_location(job: dict, profile: dict) -> float:
    """0–20. This is the fix for the bug where Tel Aviv and São Paulo roles
    outranked London ones — location now carries real weight, not zero."""
    location = job.get("location") or ""
    if _LONDON_UK.search(location):
        return 20.0
    targets = [t.lower() for t in profile.get("target_locations", []) if "remote" not in t.lower()]
    if any(t in location.lower() for t in targets):
        return 20.0
    if job.get("remote") is True:
        return 12.0
    if not location.strip():
        return 6.0
    return 0.0


def score_skill_overlap(job_words: set[str], profile: dict) -> tuple[float, set[str]]:
    """0–25, scaled against the profile's own skill vocabulary rather than every
    word in the posting — so a long JD full of boilerplate can't dilute this."""
    skills = skill_tokens(profile)
    overlap = job_words & skills
    if not skills:
        return 0.0, overlap
    ratio = len(overlap) / len(skills)
    return min(25.0, ratio * 60), overlap


def extract_requirements(description: str) -> list[str]:
    """Bullet-list lines from the posting — usually the Requirements section."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in _REQ_LINE.findall(description or ""):
        line = raw.strip()
        key = line.lower()
        if 12 <= len(line) <= 240 and key not in seen:
            seen.add(key)
            out.append(line)
    return out[:12]


def match_requirements(description: str, profile: dict) -> list[dict]:
    """Each requirement line against the bullet bank and skill list.

    This is doing the same job the model does in JobAnalysis.must_haves, just
    with word overlap instead of judgment — it can tell you 'design systems'
    appears in both places, not whether your version of it is deep enough. Read
    the evidence, don't just trust the status label.
    """
    reqs = extract_requirements(description)
    if not reqs:
        return []
    bindex = bullet_index(profile)
    skills = skill_tokens(profile)
    out = []
    for req in reqs:
        rwords = tokens(req)
        best_id, best_hits = "", 0
        for bid, bwords in bindex.items():
            hits = len(rwords & bwords)
            if hits > best_hits:
                best_id, best_hits = bid, hits
        skill_hits = len(rwords & skills)
        if best_hits >= 2 or best_hits + skill_hits >= 3:
            status = "met"
        elif best_hits + skill_hits >= 1:
            status = "partial"
        else:
            status = "gap"
        evidence = (
            best_id if best_hits > 0 else ("your skills list" if skill_hits > 0 else "no match in your profile")
        )
        out.append({"requirement": req, "status": status, "evidence": evidence})
    return out


def heuristic_analysis(job: dict, profile: dict) -> dict:
    """Weighted, explainable scoring: title fit + skill overlap + location + the
    two deterministic risk scans. No model, no judgment about depth or tone —
    just the things a spreadsheet could check, checked properly."""
    description = job.get("description") or ""
    job_words = tokens(f"{job.get('title', '')} {description}")
    overlap = job_words & profile_tokens(profile)
    missing = sorted(job_words - profile_tokens(profile))[:20]

    title_score = score_role_title(job.get("title", ""), profile)
    skill_score, _ = score_skill_overlap(job_words, profile)
    location_score = score_location(job, profile)
    # A small residual credit for general overlap, so two postings tied on
    # title/skill/location don't score identically regardless of everything else.
    overlap_bonus = min(10.0, 30.0 * len(overlap) / len(job_words)) if job_words else 0.0

    score = title_score + skill_score + location_score + overlap_bonus

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

    if location_score == 0 and (job.get("location") or "").strip():
        risks.append(f"Location doesn't match your targets: {job.get('location')}")

    must_haves = match_requirements(description, profile)
    gaps = [r for r in must_haves if r["status"] == "gap"]
    if len(gaps) >= 3:
        score -= 6

    # Capped below the range a real assessment uses, so a heuristic score never
    # reads as a confident verdict.
    score = max(0, min(72, round(score)))

    bits = []
    bits.append("title matches" if title_score >= 25 else "title is adjacent" if title_score else "title doesn't match your target roles")
    if location_score >= 20:
        bits.append("right location")
    elif location_score == 0 and (job.get("location") or "").strip():
        bits.append("wrong location")
    if gaps:
        bits.append(f"{len(gaps)} likely gap(s)")

    return {
        "engine": "keyword",
        "fit_score": score,
        "verdict": "possible" if score >= 45 else "weak",
        "one_line": (
            f"Keyword estimate, capped at 72 — {', '.join(bits)}. "
            "Set ANTHROPIC_API_KEY for a real assessment."
        ),
        "role_family": "",
        "seniority": f"posting asks for {years}+ years" if years else "",
        "work_authorisation": work_auth,
        "must_haves": must_haves,
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
