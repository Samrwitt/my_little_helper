from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utcnow
from app.models import Scholarship, ScholarshipMatch, User
from app.services.ai.gemini import GeminiService


class EligibilityAgent:
    def __init__(self, db: AsyncSession, gemini: GeminiService | None = None):
        self.db = db
        self.gemini = gemini or GeminiService()

    async def evaluate(self, user_id: UUID, scholarship_id: UUID) -> ScholarshipMatch:
        user = (
            await self.db.execute(
                select(User).options(selectinload(User.profile)).where(User.id == user_id)
            )
        ).scalar_one()
        scholarship = (
            await self.db.execute(
                select(Scholarship)
                .options(selectinload(Scholarship.documents))
                .where(Scholarship.id == scholarship_id)
            )
        ).scalar_one()

        profile = user.profile
        profile_dict = {
            "nationality": profile.nationality if profile else None,
            "country_of_residence": profile.country_of_residence if profile else None,
            "highest_degree": profile.highest_degree if profile else None,
            "target_degree": profile.target_degree if profile else None,
            "fields": (profile.fields if profile else []) or [],
            "graduation_year": profile.graduation_year if profile else None,
            "gpa": profile.gpa if profile else None,
            "english_tests": (profile.english_tests if profile else {}) or {},
            "work_experience_years": profile.work_experience_years if profile else None,
            "preferred_countries": (profile.preferred_countries if profile else []) or [],
            "funding_preference": profile.funding_preference if profile else None,
            "age": profile.age if profile else None,
        }
        scholarship_dict = {
            "name": scholarship.name,
            "eligible_nationalities": scholarship.eligible_nationalities or [],
            "degree_levels": scholarship.degree_levels or [],
            "fields_of_study": scholarship.fields_of_study or [],
            "minimum_gpa": scholarship.minimum_gpa,
            "required_degree": scholarship.required_degree,
            "minimum_work_experience": scholarship.minimum_work_experience,
            "language_requirements": scholarship.language_requirements,
            "age_requirement": scholarship.age_requirement,
            "required_documents": [d.name for d in (scholarship.documents or [])],
            "funding_type": scholarship.funding_type.value if scholarship.funding_type else None,
            "verification_status": scholarship.verification_status.value
            if scholarship.verification_status
            else None,
            "fact_statuses": scholarship.fact_statuses or {},
        }

        evaluation = self.gemini.evaluate_eligibility(profile_dict, scholarship_dict)

        existing = (
            await self.db.execute(
                select(ScholarshipMatch).where(
                    ScholarshipMatch.user_id == user_id,
                    ScholarshipMatch.scholarship_id == scholarship_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            match = existing
        else:
            match = ScholarshipMatch(user_id=user_id, scholarship_id=scholarship_id)
            self.db.add(match)

        match.status = evaluation.status
        match.matched_requirements = evaluation.matched_requirements
        match.missing_requirements = evaluation.missing_requirements
        match.failed_requirements = evaluation.failed_requirements
        match.unknown_requirements = evaluation.unknown_requirements
        match.reasoning_summary = evaluation.reasoning_summary
        match.confidence = evaluation.confidence
        match.evaluated_at = utcnow()
        await self.db.flush()
        return match

    async def recompute_for_user(self, user_id: UUID) -> int:
        scholarships = (
            await self.db.execute(select(Scholarship).where(Scholarship.is_active.is_(True)))
        ).scalars().all()
        count = 0
        for s in scholarships:
            await self.evaluate(user_id, s.id)
            count += 1
        return count

    async def recompute_for_scholarship(self, scholarship_id: UUID) -> int:
        matches = (
            await self.db.execute(
                select(ScholarshipMatch).where(ScholarshipMatch.scholarship_id == scholarship_id)
            )
        ).scalars().all()
        for m in matches:
            await self.evaluate(m.user_id, scholarship_id)
        return len(matches)
