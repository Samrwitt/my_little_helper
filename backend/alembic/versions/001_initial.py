"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    funding_type = postgresql.ENUM(
        "fully_funded", "partial", "tuition_only", "stipend_only", "unknown",
        name="funding_type",
        create_type=False,
    )
    verification_status = postgresql.ENUM(
        "verified", "unverified", "unknown", "failed", name="verification_status", create_type=False
    )
    fact_status = postgresql.ENUM(
        "verified", "unverified", "unknown", name="fact_status", create_type=False
    )
    doc_fact_status = postgresql.ENUM(
        "verified", "unverified", "unknown", name="doc_fact_status", create_type=False
    )
    eligibility_status = postgresql.ENUM(
        "eligible", "likely_eligible", "uncertain", "likely_ineligible", "ineligible",
        name="eligibility_status",
        create_type=False,
    )
    application_status = postgresql.ENUM(
        "discovered", "saved", "preparing", "ready_to_apply", "applied",
        "interview", "awarded", "rejected", "withdrawn",
        name="application_status",
        create_type=False,
    )
    reminder_type = postgresql.ENUM(
        "deadline", "document", "change", "custom", name="reminder_type", create_type=False
    )
    notification_channel = postgresql.ENUM(
        "in_app", "email", "telegram", "sms", "whatsapp", "push", "google_calendar",
        name="notification_channel",
        create_type=False,
    )
    agent_run_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", "cancelled",
        name="agent_run_status",
        create_type=False,
    )
    change_type = postgresql.ENUM(
        "deadline_changed", "requirements_changed", "funding_changed",
        "eligible_countries_changed", "application_opened", "application_closed", "other",
        name="change_type",
        create_type=False,
    )

    for enum in [
        funding_type, verification_status, fact_status, doc_fact_status,
        eligibility_status, application_status, reminder_type,
        notification_channel, agent_run_status, change_type,
    ]:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("nationality", sa.String(100)),
        sa.Column("country_of_residence", sa.String(100)),
        sa.Column("highest_degree", sa.String(255)),
        sa.Column("target_degree", sa.String(100)),
        sa.Column("fields", postgresql.ARRAY(sa.String())),
        sa.Column("graduation_year", sa.Integer()),
        sa.Column("gpa", sa.Float()),
        sa.Column("english_tests", postgresql.JSONB()),
        sa.Column("work_experience_years", sa.Float()),
        sa.Column("preferred_countries", postgresql.ARRAY(sa.String())),
        sa.Column("funding_preference", sa.String(50)),
        sa.Column("age", sa.Integer()),
        sa.Column("extra", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "scholarships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("provider", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("official_url", sa.String(2048)),
        sa.Column("normalized_url", sa.String(2048)),
        sa.Column("country", sa.String(100)),
        sa.Column("host_institution", sa.String(255)),
        sa.Column("degree_levels", postgresql.ARRAY(sa.String())),
        sa.Column("fields_of_study", postgresql.ARRAY(sa.String())),
        sa.Column("eligible_nationalities", postgresql.ARRAY(sa.String())),
        sa.Column("funding_type", funding_type, nullable=False),
        sa.Column("tuition_coverage", sa.Boolean()),
        sa.Column("stipend", sa.String(255)),
        sa.Column("travel_coverage", sa.Boolean()),
        sa.Column("insurance_coverage", sa.Boolean()),
        sa.Column("accommodation_coverage", sa.Boolean()),
        sa.Column("application_open_date", sa.Date()),
        sa.Column("application_deadline", sa.Date()),
        sa.Column("minimum_gpa", sa.Float()),
        sa.Column("required_degree", sa.String(255)),
        sa.Column("minimum_work_experience", sa.Float()),
        sa.Column("language_requirements", sa.Text()),
        sa.Column("age_requirement", sa.String(255)),
        sa.Column("application_process", sa.Text()),
        sa.Column("source_reliability", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("application_year", sa.Integer()),
        sa.Column("fact_statuses", postgresql.JSONB()),
        sa.Column("confidence", sa.Float()),
        sa.Column("search_vector", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scholarships_official_url", "scholarships", ["official_url"])
    op.create_index("ix_scholarships_normalized_url", "scholarships", ["normalized_url"])
    op.create_index("ix_scholarships_deadline", "scholarships", ["application_deadline"])
    op.create_index("ix_scholarships_country", "scholarships", ["country"])
    op.create_index("ix_scholarships_name_trgm", "scholarships", ["name"])

    op.create_table(
        "scholarship_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("reliability_level", sa.Integer()),
        sa.Column("trust_score", sa.Float()),
        sa.Column("is_official", sa.Boolean()),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scholarship_sources_scholarship_id", "scholarship_sources", ["scholarship_id"])

    op.create_table(
        "scholarship_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean()),
        sa.Column("fact_status", fact_status),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("extra", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "scholarship_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_required", sa.Boolean()),
        sa.Column("fact_status", doc_fact_status),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "scholarship_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_type", change_type, nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("previous_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("notified", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "scholarship_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", eligibility_status),
        sa.Column("matched_requirements", postgresql.JSONB()),
        sa.Column("missing_requirements", postgresql.JSONB()),
        sa.Column("failed_requirements", postgresql.JSONB()),
        sa.Column("unknown_requirements", postgresql.JSONB()),
        sa.Column("reasoning_summary", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("evaluated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "scholarship_id", name="uq_user_scholarship_match"),
    )

    op.create_table(
        "saved_scholarships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "scholarship_id", name="uq_user_saved_scholarship"),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", application_status),
        sa.Column("readiness_percent", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "scholarship_id", name="uq_user_application"),
    )
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "application_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_complete", sa.Boolean()),
        sa.Column("scholarship_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarship_documents.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scholarship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scholarships.id", ondelete="CASCADE")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE")),
        sa.Column("reminder_type", reminder_type),
        sa.Column("days_before", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent", sa.Boolean()),
        sa.Column("cancelled", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reminders_scheduled_for", "reminders", ["scheduled_for"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", notification_channel),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(2048)),
        sa.Column("is_read", sa.Boolean()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", agent_run_status),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("decision_summary", sa.Text()),
        sa.Column("search_queries", postgresql.JSONB()),
        sa.Column("scholarships_discovered", sa.Integer()),
        sa.Column("scholarships_saved", sa.Integer()),
        sa.Column("errors", postgresql.JSONB()),
        sa.Column("token_usage", postgresql.JSONB()),
        sa.Column("estimated_api_cost", sa.Float()),
        sa.Column("input_payload", postgresql.JSONB()),
        sa.Column("output_payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"])

    op.create_table(
        "agent_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_data", postgresql.JSONB()),
        sa.Column("output_data", postgresql.JSONB()),
        sa.Column("success", sa.Boolean()),
        sa.Column("error_message", sa.Text()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "agent_tool_calls", "agent_runs", "notifications", "reminders",
        "application_documents", "applications", "saved_scholarships",
        "scholarship_matches", "scholarship_changes", "scholarship_documents",
        "scholarship_requirements", "scholarship_sources", "scholarships",
        "user_profiles", "refresh_tokens", "users",
    ]:
        op.drop_table(table)
    for enum_name in [
        "change_type", "agent_run_status", "notification_channel", "reminder_type",
        "application_status", "eligibility_status", "doc_fact_status", "fact_status",
        "verification_status", "funding_type",
    ]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
