from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import (
    ApplicationCreate,
    ApplicationDocumentUpdate,
    ApplicationOut,
    ApplicationUpdate,
    ScholarshipListItem,
)
from app.services.applications import ApplicationService
from app.services.scholarships import days_remaining

router = APIRouter(prefix="/applications", tags=["applications"])


def _to_out(app) -> ApplicationOut:
    s = app.scholarship
    sch = None
    if s:
        sch = ScholarshipListItem(
            id=s.id,
            name=s.name,
            provider=s.provider,
            country=s.country,
            host_institution=s.host_institution,
            degree_levels=s.degree_levels or [],
            fields_of_study=s.fields_of_study or [],
            funding_type=s.funding_type,
            tuition_coverage=s.tuition_coverage,
            stipend=s.stipend,
            travel_coverage=s.travel_coverage,
            insurance_coverage=s.insurance_coverage,
            accommodation_coverage=s.accommodation_coverage,
            application_deadline=s.application_deadline,
            days_remaining=days_remaining(s.application_deadline),
            verification_status=s.verification_status,
            source_reliability=s.source_reliability,
            application_status=app.status,
        )
    out = ApplicationOut.model_validate(app)
    out.scholarship = sch
    return out


@router.get("", response_model=list[ApplicationOut])
async def list_applications(user: CurrentUser, db: DbSession) -> list[ApplicationOut]:
    apps = await ApplicationService(db).list_for_user(user)
    return [_to_out(a) for a in apps]


@router.post("", response_model=ApplicationOut, status_code=201)
async def create_application(
    data: ApplicationCreate, user: CurrentUser, db: DbSession
) -> ApplicationOut:
    app = await ApplicationService(db).create(user, data)
    from app.services.reminders import ReminderService

    await ReminderService(db).schedule_for_scholarship(user, data.scholarship_id)
    return _to_out(app)


@router.patch("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: UUID, data: ApplicationUpdate, user: CurrentUser, db: DbSession
) -> ApplicationOut:
    app = await ApplicationService(db).update(user, application_id, data)
    return _to_out(app)


@router.patch("/{application_id}/documents/{document_id}", response_model=ApplicationOut)
async def update_document(
    application_id: UUID,
    document_id: UUID,
    data: ApplicationDocumentUpdate,
    user: CurrentUser,
    db: DbSession,
) -> ApplicationOut:
    app = await ApplicationService(db).update_document(
        user, application_id, document_id, data.is_complete, data.notes
    )
    return _to_out(app)
