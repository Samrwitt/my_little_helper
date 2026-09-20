from app.schemas import ScholarshipExtraction, EligibilityEvaluation
from app.core.enums import EligibilityStatus, FactStatus
from app.services.ai.gemini import GeminiService


def test_extraction_schema_allows_nulls():
    data = ScholarshipExtraction(
        name="Test Scholarship",
        provider=None,
        official_url=None,
        application={"opens": None, "deadline": None},
        eligibility={"minimum_gpa": None},
        confidence=0.0,
        fact_statuses={"deadline": FactStatus.UNKNOWN},
    )
    assert data.name == "Test Scholarship"
    assert data.application.deadline is None
    assert data.eligibility.minimum_gpa is None


def test_eligibility_schema():
    ev = EligibilityEvaluation(
        status=EligibilityStatus.LIKELY_ELIGIBLE,
        matched_requirements=["GPA ok"],
        missing_requirements=["IELTS"],
        failed_requirements=[],
        unknown_requirements=["Age"],
        reasoning_summary="Likely eligible with missing docs",
        confidence=0.7,
    )
    assert ev.status == EligibilityStatus.LIKELY_ELIGIBLE


def test_gemini_unavailable_without_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    service = GeminiService()
    # Force empty key
    service.settings.gemini_api_key = ""
    assert service.available is False
    get_settings.cache_clear()
