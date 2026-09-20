import enum


class ApplicationStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    SAVED = "saved"
    PREPARING = "preparing"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    INTERVIEW = "interview"
    AWARDED = "awarded"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class EligibilityStatus(str, enum.Enum):
    ELIGIBLE = "eligible"
    LIKELY_ELIGIBLE = "likely_eligible"
    UNCERTAIN = "uncertain"
    LIKELY_INELIGIBLE = "likely_ineligible"
    INELIGIBLE = "ineligible"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"
    FAILED = "failed"


class FactStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class SourceReliabilityLevel(int, enum.Enum):
    OFFICIAL = 1
    RECOGNIZED = 2
    AGGREGATOR = 3


class FundingType(str, enum.Enum):
    FULLY_FUNDED = "fully_funded"
    PARTIAL = "partial"
    TUITION_ONLY = "tuition_only"
    STIPEND_ONLY = "stipend_only"
    UNKNOWN = "unknown"


class AgentRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    GOOGLE_CALENDAR = "google_calendar"


class ReminderType(str, enum.Enum):
    DEADLINE = "deadline"
    DOCUMENT = "document"
    CHANGE = "change"
    CUSTOM = "custom"


class ChangeType(str, enum.Enum):
    DEADLINE_CHANGED = "deadline_changed"
    REQUIREMENTS_CHANGED = "requirements_changed"
    FUNDING_CHANGED = "funding_changed"
    ELIGIBLE_COUNTRIES_CHANGED = "eligible_countries_changed"
    APPLICATION_OPENED = "application_opened"
    APPLICATION_CLOSED = "application_closed"
    OTHER = "other"
