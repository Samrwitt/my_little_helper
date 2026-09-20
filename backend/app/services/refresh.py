from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ChangeType
from app.db.base import utcnow
from app.models import Scholarship, ScholarshipChange, ScholarshipMatch, User
from app.services.ai.gemini import GeminiService
from app.services.notifications import NotificationService
from app.services.scraping import ScholarshipScraper
from app.services.search.trust import classify_source


class ScholarshipRefreshService:
    def __init__(self, db: AsyncSession, gemini: GeminiService | None = None):
        self.db = db
        self.gemini = gemini or GeminiService()
        self.scraper = ScholarshipScraper()

    async def refresh(self, scholarship_id: UUID) -> list[ScholarshipChange]:
        scholarship = (
            await self.db.execute(
                select(Scholarship)
                .options(selectinload(Scholarship.sources))
                .where(Scholarship.id == scholarship_id)
            )
        ).scalar_one_or_none()
        if not scholarship or not scholarship.official_url:
            return []

        previous = self._snapshot(scholarship)
        try:
            page = await self.scraper.fetch(scholarship.official_url)
        except Exception:
            return []

        text = self.scraper.extract_text(page.html)
        if self.gemini.available:
            extraction = self.gemini.extract_scholarship(text, page.final_url)
            current = {
                "application_deadline": extraction.application.deadline.isoformat()
                if extraction.application.deadline
                else None,
                "eligible_nationalities": extraction.eligible_nationalities,
                "funding_type": "fully_funded" if extraction.funding.fully_funded else None,
                "tuition_coverage": extraction.funding.tuition,
                "stipend": extraction.funding.stipend,
                "minimum_gpa": extraction.eligibility.minimum_gpa,
                "language_requirements": extraction.eligibility.language_requirement,
                "required_degree": extraction.eligibility.degree_requirement,
            }
            # Apply non-null updates only (never invent)
            if extraction.application.deadline:
                scholarship.application_deadline = extraction.application.deadline
            if extraction.eligible_nationalities:
                scholarship.eligible_nationalities = extraction.eligible_nationalities
            if extraction.funding.tuition is not None:
                scholarship.tuition_coverage = extraction.funding.tuition
            if extraction.funding.stipend is not None:
                scholarship.stipend = extraction.funding.stipend
            if extraction.eligibility.minimum_gpa is not None:
                scholarship.minimum_gpa = extraction.eligibility.minimum_gpa
            if extraction.eligibility.language_requirement:
                scholarship.language_requirements = extraction.eligibility.language_requirement
            if extraction.eligibility.degree_requirement:
                scholarship.required_degree = extraction.eligibility.degree_requirement
        else:
            current = previous

        level, _, is_official = classify_source(page.final_url)
        if is_official:
            scholarship.verification_status = scholarship.verification_status  # keep enum
            from app.core.enums import VerificationStatus

            scholarship.verification_status = VerificationStatus.VERIFIED
            scholarship.source_reliability = level.value
        scholarship.last_verified_at = utcnow()

        diffs = self.gemini.compare_scholarship_versions(previous, self._snapshot(scholarship))
        changes: list[ScholarshipChange] = []
        for d in diffs:
            try:
                ctype = ChangeType(d.get("change_type", "other"))
            except ValueError:
                ctype = ChangeType.OTHER
            change = ScholarshipChange(
                scholarship_id=scholarship.id,
                change_type=ctype,
                field_name=d.get("field") or "unknown",
                previous_value=str(d.get("previous")),
                new_value=str(d.get("new")),
                summary=d.get("summary"),
            )
            self.db.add(change)
            changes.append(change)

        await self.db.flush()
        if changes:
            await self._notify_users(scholarship, changes)
            from app.agents.eligibility_agent import EligibilityAgent

            await EligibilityAgent(self.db, self.gemini).recompute_for_scholarship(scholarship.id)
        return changes

    def _snapshot(self, s: Scholarship) -> dict[str, Any]:
        return {
            "application_deadline": s.application_deadline.isoformat() if s.application_deadline else None,
            "eligible_nationalities": s.eligible_nationalities or [],
            "funding_type": s.funding_type.value if s.funding_type else None,
            "tuition_coverage": s.tuition_coverage,
            "stipend": s.stipend,
            "minimum_gpa": s.minimum_gpa,
            "language_requirements": s.language_requirements,
            "required_degree": s.required_degree,
        }

    async def _notify_users(self, scholarship: Scholarship, changes: list[ScholarshipChange]) -> None:
        matches = (
            await self.db.execute(
                select(ScholarshipMatch).where(ScholarshipMatch.scholarship_id == scholarship.id)
            )
        ).scalars().all()
        notifier = NotificationService(self.db)
        for m in matches:
            user = (await self.db.execute(select(User).where(User.id == m.user_id))).scalar_one()
            for change in changes:
                await notifier.create_and_send(
                    user,
                    title=f"{change.change_type.value.replace('_', ' ').title()}",
                    body=(
                        f"{scholarship.name}\nPrevious: {change.previous_value}\n"
                        f"New: {change.new_value}"
                    ),
                    link=f"/scholarships/{scholarship.id}",
                    metadata={"change_id": str(change.id)},
                )
                change.notified = True
        await self.db.flush()
