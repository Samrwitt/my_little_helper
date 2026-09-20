from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.enums import ApplicationStatus, EligibilityStatus, FundingType
from app.schemas import PaginatedScholarships, ScholarshipDetail, ScholarshipFilters
from app.services.scholarships import ScholarshipService

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


@router.get("", response_model=PaginatedScholarships)
async def list_scholarships(
    user: CurrentUser,
    db: DbSession,
    q: Optional[str] = None,
    country: Optional[str] = None,
    degree_level: Optional[str] = None,
    field: Optional[str] = None,
    funding_type: Optional[FundingType] = None,
    fully_funded: Optional[bool] = None,
    eligibility_status: Optional[EligibilityStatus] = None,
    application_status: Optional[ApplicationStatus] = None,
    deadline_before: Optional[date] = None,
    deadline_after: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedScholarships:
    filters = ScholarshipFilters(
        q=q,
        country=country,
        degree_level=degree_level,
        field=field,
        funding_type=funding_type,
        fully_funded=fully_funded,
        eligibility_status=eligibility_status,
        application_status=application_status,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        page=page,
        page_size=page_size,
    )
    return await ScholarshipService(db).list_scholarships(user, filters)


@router.get("/{scholarship_id}", response_model=ScholarshipDetail)
async def get_scholarship(
    scholarship_id: UUID, user: CurrentUser, db: DbSession
) -> ScholarshipDetail:
    return await ScholarshipService(db).get_detail(user, scholarship_id)


@router.post("/{scholarship_id}/save")
async def save_scholarship(scholarship_id: UUID, user: CurrentUser, db: DbSession) -> dict:
    row = await ScholarshipService(db).save(user, scholarship_id)
    from app.services.reminders import ReminderService

    await ReminderService(db).schedule_for_scholarship(user, scholarship_id)
    return {"id": str(row.id), "scholarship_id": str(scholarship_id), "saved": True}
