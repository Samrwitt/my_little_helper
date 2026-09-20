from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    AgentRunStatus,
    ApplicationStatus,
    ChangeType,
    EligibilityStatus,
    FactStatus,
    FundingType,
    NotificationChannel,
    ReminderType,
    SourceReliabilityLevel,
    VerificationStatus,
)
from app.db.base import Base, TimestampMixin, utcnow


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    matches: Mapped[list["ScholarshipMatch"]] = relationship(back_populates="user")
    saved_scholarships: Mapped[list["SavedScholarship"]] = relationship(back_populates="user")
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="user")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    country_of_residence: Mapped[Optional[str]] = mapped_column(String(100))
    highest_degree: Mapped[Optional[str]] = mapped_column(String(255))
    target_degree: Mapped[Optional[str]] = mapped_column(String(100))
    fields: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer)
    gpa: Mapped[Optional[float]] = mapped_column(Float)
    english_tests: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    work_experience_years: Mapped[Optional[float]] = mapped_column(Float)
    preferred_countries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    funding_preference: Mapped[Optional[str]] = mapped_column(String(50))
    age: Mapped[Optional[int]] = mapped_column(Integer)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="profile")


class Scholarship(Base, TimestampMixin):
    __tablename__ = "scholarships"
    __table_args__ = (
        Index("ix_scholarships_name_trgm", "name"),
        Index("ix_scholarships_deadline", "application_deadline"),
        Index("ix_scholarships_country", "country"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    official_url: Mapped[Optional[str]] = mapped_column(String(2048), index=True)
    normalized_url: Mapped[Optional[str]] = mapped_column(String(2048), index=True)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    host_institution: Mapped[Optional[str]] = mapped_column(String(255))
    degree_levels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    fields_of_study: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    eligible_nationalities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    funding_type: Mapped[FundingType] = mapped_column(
        Enum(FundingType, name="funding_type", values_callable=lambda x: [e.value for e in x]),
        default=FundingType.UNKNOWN,
    )
    tuition_coverage: Mapped[Optional[bool]] = mapped_column(Boolean)
    stipend: Mapped[Optional[str]] = mapped_column(String(255))
    travel_coverage: Mapped[Optional[bool]] = mapped_column(Boolean)
    insurance_coverage: Mapped[Optional[bool]] = mapped_column(Boolean)
    accommodation_coverage: Mapped[Optional[bool]] = mapped_column(Boolean)
    application_open_date: Mapped[Optional[date]] = mapped_column(Date)
    application_deadline: Mapped[Optional[date]] = mapped_column(Date)
    minimum_gpa: Mapped[Optional[float]] = mapped_column(Float)
    required_degree: Mapped[Optional[str]] = mapped_column(String(255))
    minimum_work_experience: Mapped[Optional[float]] = mapped_column(Float)
    language_requirements: Mapped[Optional[str]] = mapped_column(Text)
    age_requirement: Mapped[Optional[str]] = mapped_column(String(255))
    application_process: Mapped[Optional[str]] = mapped_column(Text)
    source_reliability: Mapped[int] = mapped_column(Integer, default=SourceReliabilityLevel.AGGREGATOR.value)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", values_callable=lambda x: [e.value for e in x]),
        default=VerificationStatus.UNVERIFIED,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    application_year: Mapped[Optional[int]] = mapped_column(Integer)
    fact_statuses: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    search_vector: Mapped[Optional[str]] = mapped_column(Text)

    sources: Mapped[list["ScholarshipSource"]] = relationship(
        back_populates="scholarship", cascade="all, delete-orphan"
    )
    requirements: Mapped[list["ScholarshipRequirement"]] = relationship(
        back_populates="scholarship", cascade="all, delete-orphan"
    )
    documents: Mapped[list["ScholarshipDocument"]] = relationship(
        back_populates="scholarship", cascade="all, delete-orphan"
    )
    changes: Mapped[list["ScholarshipChange"]] = relationship(
        back_populates="scholarship", cascade="all, delete-orphan"
    )
    matches: Mapped[list["ScholarshipMatch"]] = relationship(back_populates="scholarship")
    saved_by: Mapped[list["SavedScholarship"]] = relationship(back_populates="scholarship")
    applications: Mapped[list["Application"]] = relationship(back_populates="scholarship")


class ScholarshipSource(Base, TimestampMixin):
    __tablename__ = "scholarship_sources"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    reliability_level: Mapped[int] = mapped_column(
        Integer, default=SourceReliabilityLevel.AGGREGATOR.value
    )
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    scholarship: Mapped["Scholarship"] = relationship(back_populates="sources")


class ScholarshipRequirement(Base, TimestampMixin):
    __tablename__ = "scholarship_requirements"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    fact_status: Mapped[FactStatus] = mapped_column(
        Enum(FactStatus, name="fact_status", values_callable=lambda x: [e.value for e in x]),
        default=FactStatus.UNVERIFIED,
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    scholarship: Mapped["Scholarship"] = relationship(back_populates="requirements")


class ScholarshipDocument(Base, TimestampMixin):
    __tablename__ = "scholarship_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    fact_status: Mapped[FactStatus] = mapped_column(
        Enum(FactStatus, name="doc_fact_status", values_callable=lambda x: [e.value for e in x]),
        default=FactStatus.UNVERIFIED,
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))

    scholarship: Mapped["Scholarship"] = relationship(back_populates="documents")


class ScholarshipChange(Base, TimestampMixin):
    __tablename__ = "scholarship_changes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(ChangeType, name="change_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    scholarship: Mapped["Scholarship"] = relationship(back_populates="changes")


class ScholarshipMatch(Base, TimestampMixin):
    __tablename__ = "scholarship_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "scholarship_id", name="uq_user_scholarship_match"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[EligibilityStatus] = mapped_column(
        Enum(EligibilityStatus, name="eligibility_status", values_callable=lambda x: [e.value for e in x]),
        default=EligibilityStatus.UNCERTAIN,
    )
    matched_requirements: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    missing_requirements: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    failed_requirements: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    unknown_requirements: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    reasoning_summary: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="matches")
    scholarship: Mapped["Scholarship"] = relationship(back_populates="matches")


class SavedScholarship(Base, TimestampMixin):
    __tablename__ = "saved_scholarships"
    __table_args__ = (
        UniqueConstraint("user_id", "scholarship_id", name="uq_user_saved_scholarship"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="saved_scholarships")
    scholarship: Mapped["Scholarship"] = relationship(back_populates="saved_by")


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "scholarship_id", name="uq_user_application"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scholarship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", values_callable=lambda x: [e.value for e in x]),
        default=ApplicationStatus.SAVED,
        index=True,
    )
    readiness_percent: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="applications")
    scholarship: Mapped["Scholarship"] = relationship(back_populates="applications")
    documents: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationDocument(Base, TimestampMixin):
    __tablename__ = "application_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    scholarship_document_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarship_documents.id", ondelete="SET NULL")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    application: Mapped["Application"] = relationship(back_populates="documents")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scholarship_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True
    )
    application_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE")
    )
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, name="reminder_type", values_callable=lambda x: [e.value for e in x]),
        default=ReminderType.DEADLINE,
    )
    days_before: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="reminders")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", values_callable=lambda x: [e.value for e in x]),
        default=NotificationChannel.IN_APP,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(2048))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="notifications")


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_run_status", values_callable=lambda x: [e.value for e in x]),
        default=AgentRunStatus.PENDING,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_summary: Mapped[Optional[str]] = mapped_column(Text)
    search_queries: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    scholarships_discovered: Mapped[int] = mapped_column(Integer, default=0)
    scholarships_saved: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    estimated_api_cost: Mapped[Optional[float]] = mapped_column(Float)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    user: Mapped[Optional["User"]] = relationship(back_populates="agent_runs")
    tool_calls: Mapped[list["AgentToolCall"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan"
    )


class AgentToolCall(Base, TimestampMixin):
    __tablename__ = "agent_tool_calls"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="tool_calls")
