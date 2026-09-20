from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scholarship
from app.services.scraping.ssrf import normalize_url


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


class DeduplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_duplicate(
        self,
        *,
        name: Optional[str],
        provider: Optional[str],
        official_url: Optional[str],
        host_institution: Optional[str] = None,
        application_year: Optional[int] = None,
    ) -> Optional[Scholarship]:
        if official_url:
            normalized = normalize_url(official_url)
            result = await self.db.execute(
                select(Scholarship).where(Scholarship.normalized_url == normalized)
            )
            found = result.scalar_one_or_none()
            if found:
                return found

        if not name:
            return None

        # Candidate scan — limited set for MVP
        q = select(Scholarship).where(Scholarship.is_active.is_(True)).limit(500)
        if provider:
            q = select(Scholarship).where(
                Scholarship.is_active.is_(True),
                Scholarship.provider.ilike(f"%{provider}%"),
            ).limit(200)
        candidates = (await self.db.execute(q)).scalars().all()

        best: Optional[Scholarship] = None
        best_score = 0.0
        target = normalize_name(name)
        for c in candidates:
            score = name_similarity(target, normalize_name(c.name))
            if provider and c.provider and provider.lower() in (c.provider or "").lower():
                score += 0.1
            if host_institution and c.host_institution:
                if host_institution.lower() in c.host_institution.lower():
                    score += 0.1
            if application_year and c.application_year == application_year:
                score += 0.05
            if score > best_score:
                best_score = score
                best = c
        if best and best_score >= 0.88:
            return best
        return None
