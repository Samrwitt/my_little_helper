from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import ScholarshipMatch
from app.schemas import MatchOut, ScholarshipListItem
from app.services.scholarships import days_remaining

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
async def list_matches(user: CurrentUser, db: DbSession) -> list[MatchOut]:
    result = await db.execute(
        select(ScholarshipMatch)
        .options(selectinload(ScholarshipMatch.scholarship))
        .where(ScholarshipMatch.user_id == user.id)
        .order_by(ScholarshipMatch.confidence.desc())
    )
    matches = result.scalars().all()
    out: list[MatchOut] = []
    for m in matches:
        s = m.scholarship
        item = None
        if s:
            item = ScholarshipListItem(
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
                eligibility_status=m.status,
            )
        data = MatchOut.model_validate(m)
        data.scholarship = item
        out.append(data)
    return out
