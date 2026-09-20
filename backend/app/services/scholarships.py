from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ApplicationStatus, EligibilityStatus, FundingType
from app.models import (
    Application,
    Scholarship,
    ScholarshipMatch,
    SavedScholarship,
    User,
)
from app.schemas import (
    PaginatedScholarships,
    ScholarshipDetail,
    ScholarshipFilters,
    ScholarshipListItem,
)


def days_remaining(deadline: Optional[date]) -> Optional[int]:
    if not deadline:
        return None
    today = datetime.now(timezone.utc).date()
    return (deadline - today).days


class ScholarshipService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _base_query(self):
        return select(Scholarship).where(Scholarship.is_active.is_(True))

    async def list_scholarships(
        self,
        user: User,
        filters: ScholarshipFilters,
    ) -> PaginatedScholarships:
        query = self._base_query()
        conditions = []

        if filters.q:
            pattern = f"%{filters.q}%"
            conditions.append(
                or_(
                    Scholarship.name.ilike(pattern),
                    Scholarship.provider.ilike(pattern),
                    Scholarship.description.ilike(pattern),
                    Scholarship.host_institution.ilike(pattern),
                )
            )
        if filters.country:
            conditions.append(Scholarship.country.ilike(f"%{filters.country}%"))
        if filters.degree_level:
            conditions.append(Scholarship.degree_levels.any(filters.degree_level))
        if filters.field:
            conditions.append(Scholarship.fields_of_study.any(filters.field))
        if filters.funding_type:
            conditions.append(Scholarship.funding_type == filters.funding_type)
        if filters.fully_funded:
            conditions.append(Scholarship.funding_type == FundingType.FULLY_FUNDED)
        if filters.deadline_before:
            conditions.append(Scholarship.application_deadline <= filters.deadline_before)
        if filters.deadline_after:
            conditions.append(Scholarship.application_deadline >= filters.deadline_after)

        if conditions:
            query = query.where(and_(*conditions))

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            query.order_by(Scholarship.application_deadline.asc().nulls_last())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        rows = (await self.db.execute(query)).scalars().all()

        match_map = await self._matches_for_user(user.id, [s.id for s in rows])
        app_map = await self._apps_for_user(user.id, [s.id for s in rows])

        items: list[ScholarshipListItem] = []
        for s in rows:
            if filters.eligibility_status:
                m = match_map.get(s.id)
                if not m or m.status != filters.eligibility_status:
                    continue
            if filters.application_status:
                a = app_map.get(s.id)
                if not a or a.status != filters.application_status:
                    continue
            items.append(self._to_list_item(s, match_map.get(s.id), app_map.get(s.id)))

        return PaginatedScholarships(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def get_detail(self, user: User, scholarship_id: UUID) -> ScholarshipDetail:
        result = await self.db.execute(
            select(Scholarship)
            .options(
                selectinload(Scholarship.sources),
                selectinload(Scholarship.requirements),
                selectinload(Scholarship.documents),
                selectinload(Scholarship.changes),
            )
            .where(Scholarship.id == scholarship_id)
        )
        scholarship = result.scalar_one_or_none()
        if not scholarship:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found")

        match_map = await self._matches_for_user(user.id, [scholarship.id])
        app_map = await self._apps_for_user(user.id, [scholarship.id])
        base = self._to_list_item(
            scholarship, match_map.get(scholarship.id), app_map.get(scholarship.id)
        )
        match = match_map.get(scholarship.id)
        from app.schemas import MatchOut

        detail = ScholarshipDetail(
            **base.model_dump(),
            description=scholarship.description,
            official_url=scholarship.official_url,
            eligible_nationalities=scholarship.eligible_nationalities or [],
            application_open_date=scholarship.application_open_date,
            minimum_gpa=scholarship.minimum_gpa,
            required_degree=scholarship.required_degree,
            minimum_work_experience=scholarship.minimum_work_experience,
            language_requirements=scholarship.language_requirements,
            age_requirement=scholarship.age_requirement,
            application_process=scholarship.application_process,
            fact_statuses=scholarship.fact_statuses or {},
            confidence=scholarship.confidence,
            last_verified_at=scholarship.last_verified_at,
            sources=scholarship.sources,
            requirements=scholarship.requirements,
            documents=scholarship.documents,
            changes=sorted(scholarship.changes, key=lambda c: c.created_at, reverse=True)[:20],
            match=MatchOut.model_validate(match) if match else None,
        )
        return detail

    async def save(self, user: User, scholarship_id: UUID) -> SavedScholarship:
        existing = await self.db.execute(
            select(SavedScholarship).where(
                SavedScholarship.user_id == user.id,
                SavedScholarship.scholarship_id == scholarship_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = SavedScholarship(user_id=user.id, scholarship_id=scholarship_id)
        self.db.add(row)
        # Ensure application pipeline entry exists
        app_existing = await self.db.execute(
            select(Application).where(
                Application.user_id == user.id,
                Application.scholarship_id == scholarship_id,
            )
        )
        if not app_existing.scalar_one_or_none():
            from app.services.applications import ApplicationService

            await ApplicationService(self.db).create_from_scholarship(
                user, scholarship_id, ApplicationStatus.SAVED
            )
        await self.db.flush()
        return row

    async def _matches_for_user(self, user_id: UUID, scholarship_ids: list[UUID]):
        if not scholarship_ids:
            return {}
        result = await self.db.execute(
            select(ScholarshipMatch).where(
                ScholarshipMatch.user_id == user_id,
                ScholarshipMatch.scholarship_id.in_(scholarship_ids),
            )
        )
        return {m.scholarship_id: m for m in result.scalars().all()}

    async def _apps_for_user(self, user_id: UUID, scholarship_ids: list[UUID]):
        if not scholarship_ids:
            return {}
        result = await self.db.execute(
            select(Application).where(
                Application.user_id == user_id,
                Application.scholarship_id.in_(scholarship_ids),
            )
        )
        return {a.scholarship_id: a for a in result.scalars().all()}

    def _to_list_item(
        self,
        s: Scholarship,
        match: Optional[ScholarshipMatch],
        app: Optional[Application],
    ) -> ScholarshipListItem:
        return ScholarshipListItem(
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
            eligibility_status=match.status if match else None,
            application_status=app.status if app else None,
        )
