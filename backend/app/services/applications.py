from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ApplicationStatus
from app.models import Application, ApplicationDocument, Scholarship, ScholarshipDocument, User
from app.schemas import ApplicationCreate, ApplicationUpdate


class ApplicationService:
    TERMINAL_STATUSES = {
        ApplicationStatus.SUBMITTED
        if False
        else ApplicationStatus.APPLIED,  # keep applied as non-terminal for reminders until submitted-like
    }

    REMINDER_STOP_STATUSES = {
        ApplicationStatus.APPLIED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.AWARDED,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user: User) -> list[Application]:
        result = await self.db.execute(
            select(Application)
            .options(
                selectinload(Application.documents),
                selectinload(Application.scholarship),
            )
            .where(Application.user_id == user.id)
            .order_by(Application.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, user: User, data: ApplicationCreate) -> Application:
        return await self.create_from_scholarship(user, data.scholarship_id, data.status, data.notes)

    async def create_from_scholarship(
        self,
        user: User,
        scholarship_id: UUID,
        status_value: ApplicationStatus = ApplicationStatus.SAVED,
        notes: str | None = None,
    ) -> Application:
        existing = await self.db.execute(
            select(Application)
            .options(selectinload(Application.documents))
            .where(
                Application.user_id == user.id,
                Application.scholarship_id == scholarship_id,
            )
        )
        app = existing.scalar_one_or_none()
        if app:
            return app

        scholarship = (
            await self.db.execute(
                select(Scholarship)
                .options(selectinload(Scholarship.documents))
                .where(Scholarship.id == scholarship_id)
            )
        ).scalar_one_or_none()
        if not scholarship:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found")

        app = Application(
            user_id=user.id,
            scholarship_id=scholarship_id,
            status=status_value,
            notes=notes,
        )
        self.db.add(app)
        await self.db.flush()

        docs = scholarship.documents or []
        if not docs:
            # Default checklist when scholarship has no extracted docs yet
            for name in ["CV", "Transcript", "Motivation Letter", "Recommendation Letter", "Passport"]:
                self.db.add(
                    ApplicationDocument(application_id=app.id, name=name, is_complete=False)
                )
        else:
            for doc in docs:
                self.db.add(
                    ApplicationDocument(
                        application_id=app.id,
                        name=doc.name,
                        scholarship_document_id=doc.id,
                        is_complete=False,
                    )
                )
        await self.db.flush()
        await self._recalculate_readiness(app.id)
        result = await self.db.execute(
            select(Application)
            .options(
                selectinload(Application.documents),
                selectinload(Application.scholarship),
            )
            .where(Application.id == app.id)
        )
        return result.scalar_one()

    async def update(self, user: User, application_id: UUID, data: ApplicationUpdate) -> Application:
        app = await self._get_owned(user, application_id)
        if data.status is not None:
            app.status = data.status
            if data.status == ApplicationStatus.APPLIED:
                app.submitted_at = datetime.now(timezone.utc)
            if data.status in self.REMINDER_STOP_STATUSES:
                from app.services.reminders import ReminderService

                await ReminderService(self.db).cancel_for_application(app.id)
        if data.notes is not None:
            app.notes = data.notes
        await self.db.flush()
        return await self._get_owned(user, application_id)

    async def update_document(
        self,
        user: User,
        application_id: UUID,
        document_id: UUID,
        is_complete: bool,
        notes: str | None = None,
    ) -> Application:
        app = await self._get_owned(user, application_id)
        doc = next((d for d in app.documents if d.id == document_id), None)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        doc.is_complete = is_complete
        if notes is not None:
            doc.notes = notes
        await self.db.flush()
        await self._recalculate_readiness(app.id)
        # Auto-advance to preparing / ready
        await self.db.refresh(app)
        if app.readiness_percent >= 100 and app.status in {
            ApplicationStatus.SAVED,
            ApplicationStatus.PREPARING,
            ApplicationStatus.DISCOVERED,
        }:
            app.status = ApplicationStatus.READY_TO_APPLY
        elif app.readiness_percent > 0 and app.status == ApplicationStatus.SAVED:
            app.status = ApplicationStatus.PREPARING
        await self.db.flush()
        return await self._get_owned(user, application_id)

    async def _recalculate_readiness(self, application_id: UUID) -> float:
        result = await self.db.execute(
            select(Application)
            .options(selectinload(Application.documents))
            .where(Application.id == application_id)
        )
        app = result.scalar_one()
        docs = app.documents
        if not docs:
            app.readiness_percent = 0.0
        else:
            done = sum(1 for d in docs if d.is_complete)
            app.readiness_percent = round(100.0 * done / len(docs), 1)
        await self.db.flush()
        return app.readiness_percent

    async def _get_owned(self, user: User, application_id: UUID) -> Application:
        result = await self.db.execute(
            select(Application)
            .options(
                selectinload(Application.documents),
                selectinload(Application.scholarship),
            )
            .where(Application.id == application_id, Application.user_id == user.id)
        )
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        return app
