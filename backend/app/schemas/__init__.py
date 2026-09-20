from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.core.enums import (
    ApplicationStatus,
    EligibilityStatus,
    FactStatus,
    FundingType,
    VerificationStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str]
    is_active: bool
    onboarding_completed: bool
    created_at: datetime


# --- Profile ---


class EnglishTests(BaseModel):
    ielts: Optional[float] = None
    toefl: Optional[float] = None


class ProfileUpdate(BaseModel):
    nationality: Optional[str] = None
    country_of_residence: Optional[str] = None
    highest_degree: Optional[str] = None
    target_degree: Optional[str] = None
    fields: list[str] = Field(default_factory=list)
    graduation_year: Optional[int] = None
    gpa: Optional[float] = Field(default=None, ge=0, le=4.0)
    english_tests: EnglishTests = Field(default_factory=EnglishTests)
    work_experience_years: Optional[float] = Field(default=None, ge=0)
    preferred_countries: list[str] = Field(default_factory=list)
    funding_preference: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)


class ProfileOut(ORMModel):
    id: UUID
    user_id: UUID
    nationality: Optional[str]
    country_of_residence: Optional[str]
    highest_degree: Optional[str]
    target_degree: Optional[str]
    fields: list[str]
    graduation_year: Optional[int]
    gpa: Optional[float]
    english_tests: dict[str, Any]
    work_experience_years: Optional[float]
    preferred_countries: list[str]
    funding_preference: Optional[str]
    age: Optional[int]


# --- Scholarships ---


class ScholarshipSourceOut(ORMModel):
    id: UUID
    url: str
    title: Optional[str]
    reliability_level: int
    trust_score: float
    is_official: bool
    last_fetched_at: Optional[datetime]


class ScholarshipDocumentOut(ORMModel):
    id: UUID
    name: str
    description: Optional[str]
    is_required: bool
    fact_status: FactStatus
    source_url: Optional[str]


class ScholarshipRequirementOut(ORMModel):
    id: UUID
    category: str
    description: str
    is_mandatory: bool
    fact_status: FactStatus
    source_url: Optional[str]


class ScholarshipChangeOut(ORMModel):
    id: UUID
    change_type: str
    field_name: str
    previous_value: Optional[str]
    new_value: Optional[str]
    summary: Optional[str]
    created_at: datetime


class ScholarshipListItem(ORMModel):
    id: UUID
    name: str
    provider: Optional[str]
    country: Optional[str]
    host_institution: Optional[str]
    degree_levels: list[str]
    fields_of_study: list[str]
    funding_type: FundingType
    tuition_coverage: Optional[bool]
    stipend: Optional[str]
    travel_coverage: Optional[bool]
    insurance_coverage: Optional[bool]
    accommodation_coverage: Optional[bool]
    application_deadline: Optional[date]
    days_remaining: Optional[int] = None
    verification_status: VerificationStatus
    source_reliability: int
    eligibility_status: Optional[EligibilityStatus] = None
    application_status: Optional[ApplicationStatus] = None


class ScholarshipDetail(ScholarshipListItem):
    description: Optional[str]
    official_url: Optional[str]
    eligible_nationalities: list[str]
    application_open_date: Optional[date]
    minimum_gpa: Optional[float]
    required_degree: Optional[str]
    minimum_work_experience: Optional[float]
    language_requirements: Optional[str]
    age_requirement: Optional[str]
    application_process: Optional[str]
    fact_statuses: dict[str, Any]
    confidence: Optional[float]
    last_verified_at: Optional[datetime]
    sources: list[ScholarshipSourceOut] = Field(default_factory=list)
    requirements: list[ScholarshipRequirementOut] = Field(default_factory=list)
    documents: list[ScholarshipDocumentOut] = Field(default_factory=list)
    changes: list[ScholarshipChangeOut] = Field(default_factory=list)
    match: Optional["MatchOut"] = None


class ScholarshipFilters(BaseModel):
    q: Optional[str] = None
    country: Optional[str] = None
    degree_level: Optional[str] = None
    field: Optional[str] = None
    funding_type: Optional[FundingType] = None
    fully_funded: Optional[bool] = None
    eligibility_status: Optional[EligibilityStatus] = None
    application_status: Optional[ApplicationStatus] = None
    deadline_before: Optional[date] = None
    deadline_after: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedScholarships(BaseModel):
    items: list[ScholarshipListItem]
    total: int
    page: int
    page_size: int


# --- Matches ---


class MatchOut(ORMModel):
    id: UUID
    scholarship_id: UUID
    status: EligibilityStatus
    matched_requirements: list[Any]
    missing_requirements: list[Any]
    failed_requirements: list[Any]
    unknown_requirements: list[Any]
    reasoning_summary: Optional[str]
    confidence: float
    evaluated_at: datetime
    scholarship: Optional[ScholarshipListItem] = None


# --- Applications ---


class ApplicationDocumentOut(ORMModel):
    id: UUID
    name: str
    is_complete: bool
    notes: Optional[str]


class ApplicationDocumentUpdate(BaseModel):
    is_complete: bool
    notes: Optional[str] = None


class ApplicationCreate(BaseModel):
    scholarship_id: UUID
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None


class ApplicationOut(ORMModel):
    id: UUID
    scholarship_id: UUID
    status: ApplicationStatus
    readiness_percent: float
    notes: Optional[str]
    submitted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    documents: list[ApplicationDocumentOut] = Field(default_factory=list)
    scholarship: Optional[ScholarshipListItem] = None


# --- Reminders / Notifications ---


class ReminderOut(ORMModel):
    id: UUID
    scholarship_id: Optional[UUID]
    days_before: int
    scheduled_for: datetime
    title: str
    message: str
    sent: bool
    cancelled: bool


class NotificationOut(ORMModel):
    id: UUID
    channel: str
    title: str
    body: str
    link: Optional[str]
    is_read: bool
    created_at: datetime


# --- Dashboard ---


class DashboardStats(BaseModel):
    matched_scholarships: int
    applications_in_progress: int
    deadlines_this_month: int
    applications_submitted: int


class UpcomingDeadline(BaseModel):
    scholarship_id: UUID
    name: str
    deadline: Optional[date]
    days_remaining: Optional[int]
    eligibility_status: Optional[EligibilityStatus]
    funding: dict[str, Any]
    missing_requirements: list[Any]
    application_status: Optional[ApplicationStatus]


class DashboardOut(BaseModel):
    stats: DashboardStats
    upcoming_deadlines: list[UpcomingDeadline]
    recent_notifications: list[NotificationOut]


# --- Agent ---


class DiscoverRequest(BaseModel):
    max_results: int = Field(default=10, ge=1, le=30)


class AgentRunOut(ORMModel):
    id: UUID
    agent_name: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    decision_summary: Optional[str]
    scholarships_discovered: int
    scholarships_saved: int
    errors: list[Any]
    estimated_api_cost: Optional[float]


# --- Extraction schema (Gemini structured output) ---


class FundingExtraction(BaseModel):
    fully_funded: Optional[bool] = None
    tuition: Optional[bool] = None
    stipend: Optional[str] = None
    travel: Optional[bool] = None
    insurance: Optional[bool] = None
    accommodation: Optional[bool] = None


class ApplicationDatesExtraction(BaseModel):
    opens: Optional[date] = None
    deadline: Optional[date] = None


class EligibilityExtraction(BaseModel):
    minimum_gpa: Optional[float] = None
    degree_requirement: Optional[str] = None
    work_experience_years: Optional[float] = None
    age_limit: Optional[str] = None
    language_requirement: Optional[str] = None


class ScholarshipExtraction(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    official_url: Optional[str] = None
    country: Optional[str] = None
    host_institution: Optional[str] = None
    degree_levels: list[str] = Field(default_factory=list)
    fields_of_study: list[str] = Field(default_factory=list)
    eligible_nationalities: list[str] = Field(default_factory=list)
    funding: FundingExtraction = Field(default_factory=FundingExtraction)
    application: ApplicationDatesExtraction = Field(default_factory=ApplicationDatesExtraction)
    eligibility: EligibilityExtraction = Field(default_factory=EligibilityExtraction)
    required_documents: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    fact_statuses: dict[str, FactStatus] = Field(default_factory=dict)


class EligibilityEvaluation(BaseModel):
    status: EligibilityStatus
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    failed_requirements: list[str] = Field(default_factory=list)
    unknown_requirements: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
