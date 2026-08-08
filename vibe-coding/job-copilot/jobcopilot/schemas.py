"""Structured-output schemas. These are the contract with the model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    requirement: str = Field(description="The requirement, as the posting states it.")
    status: Literal["met", "partial", "gap"]
    evidence: str = Field(
        description=(
            "For 'met' or 'partial', the specific bullet or project from the profile "
            "that supports it. For 'gap', one line on the closest adjacent experience, "
            "or 'none' if there isn't any."
        )
    )


class WorkAuthorisation(BaseModel):
    stance: Literal["sponsors", "silent", "restricted", "excludes", "unclear"] = Field(
        description=(
            "'sponsors' if it offers sponsorship. 'excludes' only if the candidate's "
            "stated status genuinely fails the requirement — a role requiring UK right "
            "to work does not exclude a candidate who has it. 'restricted' if there is "
            "a requirement the candidate appears to meet but should confirm. "
            "'silent' if unmentioned."
        )
    )
    evidence: str = Field(
        description="Quote the posting's own words, or 'not mentioned'."
    )


class JobAnalysis(BaseModel):
    """The verdict on one posting."""

    # No ge/le bound here on purpose: structured outputs drops numeric
    # constraints and validates them client-side, so a stray 105 would fail the
    # whole analysis. It's clamped in analyze.py instead.
    fit_score: int = Field(description="0 to 100.")
    verdict: Literal["strong", "possible", "weak", "skip"]
    one_line: str = Field(description="Why this score, in one sentence.")
    role_family: str = Field(
        description="e.g. 'AI product design', 'automotive HMI', 'design systems'."
    )
    seniority: str = Field(description="Seniority the posting is pitched at.")
    work_authorisation: WorkAuthorisation
    must_haves: list[Requirement] = Field(
        description="The posting's stated requirements, assessed against the profile."
    )
    keywords: list[str] = Field(
        description="Terms an ATS would likely screen on, taken from the posting."
    )
    keywords_missing: list[str] = Field(
        description="Keywords from the posting with no honest match in the profile."
    )
    lead_projects: list[str] = Field(
        description="Project slugs to lead with, strongest first. Max three."
    )
    angle: str = Field(
        description="The positioning for this application, in two or three sentences."
    )
    risks: list[str] = Field(
        description="Reasons this could go nowhere: seniority mismatch, visa, "
        "location, missing hard requirement."
    )
    questions_to_ask: list[str] = Field(
        description="Questions worth asking them, if it gets to a conversation."
    )


class TailoredBullet(BaseModel):
    source: str = Field(
        description="The bullet-bank id this came from, e.g. 'urify.2'. Required."
    )
    text: str = Field(description="The bullet, rephrased for this posting.")


class TailoredRole(BaseModel):
    company: str
    role: str
    dates: str
    bullets: list[TailoredBullet]


class TailoredResume(BaseModel):
    """A reordered, rephrased view of the bullet bank. No new facts."""

    headline: str
    summary: str = Field(description="Two or three sentences, aimed at this posting.")
    roles: list[TailoredRole] = Field(
        description="Relevant roles, most relevant first. Drop irrelevant ones."
    )
    skills: list[str] = Field(
        description="Skills to surface for this posting, ordered by relevance."
    )
    keyword_coverage: list[str] = Field(
        description="Posting keywords this version now covers honestly."
    )
    omitted: list[str] = Field(
        description="What you left out and why, so the omission is a decision."
    )


class CoverLetter(BaseModel):
    subject: str = Field(description="Subject line if this is sent as an email.")
    body: str = Field(
        description=(
            "The letter body in Markdown. Four short paragraphs, under 250 words, "
            "in the profile's voice. No salutation placeholder like [Name] unless a "
            "real contact name is supplied."
        )
    )
    notes: list[str] = Field(
        description="Anything the writer had to guess, so it can be checked."
    )
