from calendar import monthrange
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ApplicationStatus, EligibilityStatus
from app.models import Application, Notification, Scholarship, ScholarshipMatch, User
from app.schemas import DashboardOut, DashboardStats, UpcomingDeadline
from app.services.scholarships import days_remaining


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self, user: User) -> DashboardOut:
        matched = (
            await self.db.execute(
                select(func.count())
                .select_from(ScholarshipMatch)
                .where(
                    ScholarshipMatch.user_id == user.id,
                    ScholarshipMatch.status.in_(
                        [
                            EligibilityStatus.ELIGIBLE,
                            EligibilityStatus.LIKELY_ELIGIBLE,
                            EligibilityStatus.UNCERTAIN,
                        ]
                    ),
                )
            )
        ).scalar() or 0

        in_progress = (
            await self.db.execute(
                select(func.count())
                .select_from(Application)
                .where(
                    Application.user_id == user.id,
                    Application.status.in_(
                        [
                            ApplicationStatus.SAVED,
                            ApplicationStatus.PREPARING,
                            ApplicationStatus.READY_TO_APPLY,
                            ApplicationStatus.INTERVIEW,
                        ]
                    ),
                )
            )
        ).scalar() or 0

        today = datetime.now(timezone.utc).date()
        month_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
        deadlines_this_month = (
            await self.db.execute(
                select(func.count())
                .select_from(ScholarshipMatch)
                .join(Scholarship, Scholarship.id == ScholarshipMatch.scholarship_id)
                .where(
                    ScholarshipMatch.user_id == user.id,
                    Scholarship.application_deadline >= today,
                    Scholarship.application_deadline <= month_end,
                )
            )
        ).scalar() or 0

        submitted = (
            await self.db.execute(
                select(func.count())
                .select_from(Application)
                .where(
                    Application.user_id == user.id,
                    Application.status.in_(
                        [
                            ApplicationStatus.APPLIED,
                            ApplicationStatus.INTERVIEW,
                            ApplicationStatus.AWARDED,
                        ]
                    ),
                )
            )
        ).scalar() or 0

        matches = (
            await self.db.execute(
                select(ScholarshipMatch)
                .options(selectinload(ScholarshipMatch.scholarship))
                .where(ScholarshipMatch.user_id == user.id)
            )
        ).scalars().all()

        apps = (
            await self.db.execute(
                select(Application).where(Application.user_id == user.id)
            )
        ).scalars().all()
        app_by_sch = {a.scholarship_id: a for a in apps}

        upcoming: list[UpcomingDeadline] = []
        for m in matches:
            s = m.scholarship
            if not s or not s.application_deadline:
                continue
            if s.application_deadline < today:
                continue
            app = app_by_sch.get(s.id)
            upcoming.append(
                UpcomingDeadline(
                    scholarship_id=s.id,
                    name=s.name,
                    deadline=s.application_deadline,
                    days_remaining=days_remaining(s.application_deadline),
                    eligibility_status=m.status,
                    funding={
                        "tuition": s.tuition_coverage,
                        "stipend": s.stipend,
                        "travel": s.travel_coverage,
                        "insurance": s.insurance_coverage,
                        "accommodation": s.accommodation_coverage,
                        "funding_type": s.funding_type.value if s.funding_type else None,
                    },
                    missing_requirements=m.missing_requirements or [],
                    application_status=app.status if app else None,
                )
            )
        upcoming.sort(key=lambda x: x.days_remaining if x.days_remaining is not None else 9999)

        notifications = (
            await self.db.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc())
                .limit(5)
            )
        ).scalars().all()

        from app.schemas import NotificationOut

        return DashboardOut(
            stats=DashboardStats(
                matched_scholarships=matched,
                applications_in_progress=in_progress,
                deadlines_this_month=deadlines_this_month,
                applications_submitted=submitted,
            ),
            upcoming_deadlines=upcoming[:10],
            recent_notifications=[NotificationOut.model_validate(n) for n in notifications],
        )
