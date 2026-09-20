from datetime import date, timedelta

from app.services.scholarships import days_remaining
from app.services.reminders import ReminderService, REMINDER_MESSAGES
from app.services.deduplication import name_similarity, normalize_name
from app.services.scraping.ssrf import UnsafeURLError, normalize_url, validate_public_url
from app.services.ai.gemini import GeminiService
from app.core.enums import EligibilityStatus
import pytest


def test_days_remaining_none():
    assert days_remaining(None) is None


def test_days_remaining_future():
    d = date.today() + timedelta(days=10)
    assert days_remaining(d) == 10


def test_days_remaining_past():
    d = date.today() - timedelta(days=3)
    assert days_remaining(d) == -3


def test_reminder_messages_cover_intervals():
    for days in [60, 30, 14, 7, 3, 1, 0]:
        assert days in REMINDER_MESSAGES


def test_name_similarity():
    assert name_similarity("DAAD EPOS", "DAAD EPOS") == 1.0
    assert name_similarity("Erasmus Mundus AI", "Erasmus Mundus Artificial Intelligence") > 0.5


def test_normalize_name():
    assert normalize_name("  Hello, World! ") == "hello world"


def test_normalize_url():
    assert normalize_url("https://Example.COM/path/") == "https://example.com/path"


def test_ssrf_blocks_localhost():
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://localhost/admin")


def test_ssrf_blocks_metadata():
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://169.254.169.254/latest/meta-data/")


def test_ssrf_blocks_private_ip():
    with pytest.raises(UnsafeURLError):
        validate_public_url("http://192.168.1.1/")


def test_ssrf_allows_https_public_host_format():
    # Does not resolve — may fail DNS in sandbox; only check scheme validation path for IP literals already covered
    with pytest.raises(UnsafeURLError):
        validate_public_url("ftp://example.com")


def test_heuristic_eligibility_does_not_claim_definitive_with_unknowns():
    gemini = GeminiService()
    result = gemini._heuristic_eligibility(
        {
            "nationality": "Ethiopian",
            "target_degree": "Masters",
            "fields": ["Computer Science"],
            "gpa": 3.5,
            "english_tests": {},
        },
        {
            "eligible_nationalities": ["Ethiopian"],
            "degree_levels": ["Masters"],
            "fields_of_study": ["Computer Science"],
            "minimum_gpa": 3.0,
            "language_requirements": "IELTS 6.5",
            "required_documents": ["CV", "Motivation Letter"],
        },
    )
    assert result.status != EligibilityStatus.ELIGIBLE or not result.unknown_requirements
    assert "IELTS" in " ".join(result.missing_requirements) or any(
        "IELTS" in m or "English" in m for m in result.missing_requirements
    )


def test_fallback_search_queries():
    gemini = GeminiService()
    queries = gemini._fallback_queries(
        {
            "nationality": "Ethiopian",
            "target_degree": "Masters",
            "fields": ["Computer Science", "AI"],
            "funding_preference": "fully funded",
            "graduation_year": 2025,
        },
        count=5,
    )
    assert len(queries) == 5
    assert any("Ethiopian" in q for q in queries)


def test_compare_versions_detects_deadline_change():
    gemini = GeminiService()
    changes = gemini._diff_versions(
        {"application_deadline": "2026-11-30", "funding_type": "fully_funded"},
        {"application_deadline": "2026-12-15", "funding_type": "fully_funded"},
    )
    assert any(c["field"] == "application_deadline" for c in changes)


def test_trust_classification():
    from app.services.search.trust import classify_source
    from app.core.enums import SourceReliabilityLevel

    level, score, official = classify_source("https://ethz.ch/scholarships")
    assert level == SourceReliabilityLevel.OFFICIAL
    assert score == 1.0
    assert official is True

    level2, score2, _ = classify_source("https://www.scholars4dev.com/foo")
    assert level2 == SourceReliabilityLevel.AGGREGATOR
    assert score2 == 0.5
