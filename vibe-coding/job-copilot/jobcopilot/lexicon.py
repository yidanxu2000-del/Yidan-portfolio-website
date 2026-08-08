"""Shared tokenising and profile-matching for the no-API heuristics.

Kept in one place so the scorer (analyze.py) and the bullet selector (tailor.py)
match against exactly the same vocabulary — a term the scorer credits should be
the same term the tailor can point to as evidence.
"""

from __future__ import annotations

import re

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
    "help", "make", "take", "use", "using", "join", "one", "two",
}

_WORD = re.compile(r"[a-z][a-z+#/.\-]{2,}")


def tokens(text: str) -> set[str]:
    """Words worth comparing. Trailing punctuation stripped so 'engineers.' isn't a term."""
    words = set()
    for raw in _WORD.findall((text or "").lower()):
        word = raw.strip(".-/")
        if len(word) >= 3 and word not in _STOP:
            words.add(word)
    return words


def bullet_index(profile: dict) -> dict[str, set[str]]:
    """Bullet id ('role_id.i') -> its token set (text + tags). Same ids the UI cites."""
    index: dict[str, set[str]] = {}
    for role in profile.get("experience", []):
        for i, bullet in enumerate(role.get("bullets", [])):
            text = bullet.get("text", "") + " " + " ".join(bullet.get("tags", []))
            index[f"{role['id']}.{i}"] = tokens(text)
    return index


def skill_tokens(profile: dict) -> set[str]:
    words: set[str] = set()
    for group in (profile.get("skills") or {}).values():
        for skill in group:
            words |= tokens(skill)
    return words


def profile_tokens(profile: dict) -> set[str]:
    """Every token anywhere in the profile — the vocabulary the overlap score uses."""
    text = " ".join(
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
    return tokens(text)
