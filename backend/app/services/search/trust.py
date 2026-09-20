from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

from app.core.enums import SourceReliabilityLevel

OFFICIAL_HINTS = (
    ".edu",
    ".gov",
    ".ac.uk",
    ".ac.",
    "daad.de",
    "erasmus",
    "scholarships.gov",
    "chevening.org",
    "fulbright",
    "campusfrance.org",
    "studyin",
    "ethz.ch",
    "ox.ac.uk",
    "cam.ac.uk",
    "si.se",
    "eacea.ec.europa.eu",
)

RECOGNIZED_HINTS = (
    "unesco.org",
    "britishcouncil.org",
    "iie.org",
    "scholarshipportal",
    "mastersportal",
)

AGGREGATOR_HINTS = (
    "scholars4dev",
    "scholarship-positions",
    "afterschoolafrica",
    "wemakescholars",
    "opportunitydesk",
    "youthopportunities",
)


TRUST_SCORES = {
    SourceReliabilityLevel.OFFICIAL: 1.0,
    SourceReliabilityLevel.RECOGNIZED: 0.8,
    SourceReliabilityLevel.AGGREGATOR: 0.5,
}


def classify_source(url: str, title: Optional[str] = None) -> tuple[SourceReliabilityLevel, float, bool]:
    host = (urlparse(url).netloc or "").lower()
    haystack = f"{host} {(title or '').lower()}"

    for hint in AGGREGATOR_HINTS:
        if hint in haystack:
            level = SourceReliabilityLevel.AGGREGATOR
            return level, TRUST_SCORES[level], False

    for hint in OFFICIAL_HINTS:
        if hint in haystack:
            level = SourceReliabilityLevel.OFFICIAL
            return level, TRUST_SCORES[level], True

    for hint in RECOGNIZED_HINTS:
        if hint in haystack:
            level = SourceReliabilityLevel.RECOGNIZED
            return level, TRUST_SCORES[level], False

    # Default: treat unknown as aggregator-level for caution
    level = SourceReliabilityLevel.AGGREGATOR
    return level, TRUST_SCORES[level], False


def prefer_official_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(sources, key=lambda s: s.get("trust_score", 0), reverse=True)
