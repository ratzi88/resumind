"""Small, deterministic helpers shared by job matching and roadmap views.

The embedding model is useful for broad semantic similarity, but users also
need a readable explanation. These helpers deliberately stay conservative:
they only mark a skill as present when its name (or a known alias) appears in
the resume text.
"""

from __future__ import annotations

import re
from typing import Iterable


SKILL_ALIASES = {
    "js": "javascript",
    "javascript es6": "javascript",
    "javascript es6+": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "postgres sql": "postgresql",
    "k8s": "kubernetes",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "continuous integration": "ci/cd",
    "continuous delivery": "ci/cd",
    "restful api": "rest api",
    "restful apis": "rest api",
    "apis": "api",
}


def normalize_skill_name(value: str) -> str:
    """Return a comparison-friendly representation of a skill name."""

    normalized = re.sub(r"[^a-z0-9+#/.& -]+", " ", str(value).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return SKILL_ALIASES.get(normalized, normalized)


def redact_pii(text: str) -> str:
    """Remove common contact identifiers before text reaches AI/embeddings."""

    value = str(text or "")
    value = re.sub(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", "[email]", value)
    value = re.sub(
        r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)",
        "[phone]",
        value,
    )
    return value


def parse_required_skills(value: str | None) -> list[str]:
    """Split the dataset's comma/bullet/semicolon separated skills field."""

    if not value:
        return []

    pieces = re.split(r"[,;|\n•·]+", str(value))
    result: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        skill = re.sub(r"^\s*[-*]\s*", "", piece).strip()
        skill = re.sub(r"\s+", " ", skill)
        key = normalize_skill_name(skill)
        # Ignore fragments that are clearly prose rather than skills. Short
        # labels such as "SQL" and "Git" still pass this filter.
        if not skill or len(skill) > 80 or len(key.split()) > 10 or key in seen:
            continue
        seen.add(key)
        result.append(skill)
    return result


def _skill_pattern(skill: str) -> re.Pattern[str]:
    key = normalize_skill_name(skill)
    alternatives = [re.escape(key)]
    for alias, canonical in SKILL_ALIASES.items():
        if canonical == key:
            alternatives.append(re.escape(alias))
    expression = r"(?<![a-z0-9])(?:" + "|".join(sorted(alternatives, key=len, reverse=True)) + r")(?![a-z0-9])"
    return re.compile(expression, re.IGNORECASE)


def skill_present(skill: str, resume_text: str) -> bool:
    return bool(_skill_pattern(skill).search(resume_text or ""))


def evidence_for_skill(skill: str, resume_text: str, radius: int = 100) -> str:
    """Return a short resume excerpt around the first matching skill."""

    text = re.sub(r"\s+", " ", resume_text or "").strip()
    match = _skill_pattern(skill).search(text)
    if not match:
        return ""
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt += "…"
    return excerpt


def analyze_skills(resume_text: str, required_skills: Iterable[str]) -> dict:
    """Return matched, missing, and evidence-backed skill details."""

    matched = []
    missing = []
    details = []
    for skill in required_skills:
        present = skill_present(skill, resume_text)
        detail = {
            "name": skill,
            "status": "matched" if present else "missing",
            "evidence": evidence_for_skill(skill, resume_text) if present else "",
        }
        details.append(detail)
        (matched if present else missing).append(skill)

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_details": details,
        "coverage_pct": round(len(matched) / len(details) * 100, 1) if details else None,
    }


def compute_match_pct(raw_score: float, matched_count: int = 0, required_count: int = 0) -> float:
    """Combine semantic similarity and explicit skill coverage.

    This is a product score, not a probability. Keeping the formula stable
    makes it possible to evaluate and calibrate later with labeled examples.
    """

    semantic = max(0.0, min(1.0, float(raw_score))) * 100
    coverage = (matched_count / required_count * 100) if required_count else semantic
    score = semantic * 0.75 + coverage * 0.25
    return round(max(0.0, min(100.0, score)), 1)
