from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import ApplicationStatus, ReminderType
from app.models import Application, Reminder, Scholarship, User

REMINDER_MESSAGES = {
    60: ("Start gathering documents.", "Begin collecting transcripts, CV, and recommendation letters."),
    30: ("Check transcripts and recommendation letters.", "Confirm all academic documents are ready."),
    14: ("Finish the application draft.", "Complete your motivation letter and application forms."),
    7: ("Review all required documents.", "Do a final checklist of every required upload."),
    3: ("Complete final verification.", "Verify eligibility details and submit early if possible."),
    1: ("Deadline tomorrow.", "Submit today if possible — deadline is tomorrow."),
    0: ("Application deadline today.", "Today is the deadline. Submit before the cutoff time."),
}


class ReminderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def schedule_for_scholarship(self, user: User, scholarship_id: UUID) -> list[Reminder]:
        scholarship = (
            await self.db.execute(select(Scholarship).where(Scholarship.id == scholarship_id))
        ).scalar_one_or_none()
        if not scholarship or not scholarship.application_deadline:
            return []

        app = (
            await self.db.execute(
                select(Application).where(
                    Application.user_id == user.id,
                    Application.scholarship_id == scholarship_id,
                )
            )
        ).scalar_one_or_none()
        if app and app.status in {
            ApplicationStatus.APPLIED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.AWARDED,
        }:
            return []

        # Cancel existing unsent reminders for this pair
        existing = (
            await self.db.execute(
                select(Reminder).where(
                    Reminder.user_id == user.id,
                    Reminder.scholarship_id == scholarship_id,
                    Reminder.sent.is_(False),
                    Reminder.cancelled.is_(False),
                )
            )
        ).scalars().all()
        for r in existing:
            r.cancelled = True

        created: list[Reminder] = []
        deadline = scholarship.application_deadline
        today = datetime.now(timezone.utc).date()

        for days in self.settings.reminder_intervals_days:
            remind_date = deadline - timedelta(days=days)
            if remind_date < today:
                continue
            title_suffix, message_body = REMINDER_MESSAGES.get(
                days, (f"{days} days remaining", f"{days} days until the application deadline.")
            )
            scheduled = datetime.combine(remind_date, time(9, 0), tzinfo=timezone.utc)
            reminder = Reminder(
                user_id=user.id,
                scholarship_id=scholarship_id,
                application_id=app.id if app else None,
                reminder_type=ReminderType.DEADLINE,
                days_before=days,
                scheduled_for=scheduled,
                title=f"{scholarship.name} — {title_suffix}",
                message=f"{scholarship.name}: {message_body} Deadline: {deadline.isoformat()}.",
            )
            self.db.add(reminder)
            created.append(reminder)

        await self.db.flush()
        return created

    async def cancel_for_application(self, application_id: UUID) -> None:
        rows = (
            await self.db.execute(
                select(Reminder).where(
                    Reminder.application_id == application_id,
                    Reminder.sent.is_(False),
                    Reminder.cancelled.is_(False),
                )
            )
        ).scalars().all()
        for r in rows:
            r.cancelled = True
        await self.db.flush()

    async def list_for_user(self, user: User) -> list[Reminder]:
        result = await self.db.execute(
            select(Reminder)
            .where(Reminder.user_id == user.id, Reminder.cancelled.is_(False))
            .order_by(Reminder.scheduled_for.asc())
        )
        return list(result.scalars().all())

    async def due_reminders(self, as_of: datetime | None = None) -> list[Reminder]:
        now = as_of or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Reminder).where(
                Reminder.sent.is_(False),
                Reminder.cancelled.is_(False),
                Reminder.scheduled_for <= now,
            )
        )
        return list(result.scalars().all())
