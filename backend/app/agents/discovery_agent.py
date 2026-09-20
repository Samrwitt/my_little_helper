from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    AgentRunStatus,
    FactStatus,
    FundingType,
    SourceReliabilityLevel,
    VerificationStatus,
)
from app.db.base import utcnow
from app.models import (
    AgentRun,
    AgentToolCall,
    Scholarship,
    ScholarshipDocument,
    ScholarshipRequirement,
    ScholarshipSource,
    User,
    UserProfile,
)
from app.schemas import ScholarshipExtraction
from app.services.ai.gemini import GeminiService
from app.services.deduplication import DeduplicationService
from app.services.scraping import ScholarshipScraper, UnsafeURLError, normalize_url
from app.services.search import get_search_provider
from app.services.search.trust import classify_source

logger = logging.getLogger(__name__)


class ScholarshipDiscoveryAgent:
    """
    Tool-using scholarship discovery agent.

    Gemini may propose tool calls / queries; tools are executed by this class only.
    Scraping and search are never delegated as unrestricted model actions.
    """

    def __init__(self, db: AsyncSession, gemini: Optional[GeminiService] = None):
        self.db = db
        self.gemini = gemini or GeminiService()
        self.scraper = ScholarshipScraper()
        self.search = get_search_provider()
        self.dedupe = DeduplicationService(db)
        self._tools: dict[str, Callable] = {
            "search_web": self.search_web,
            "fetch_page": self.fetch_page,
            "render_dynamic_page": self.render_dynamic_page,
            "extract_scholarship": self.extract_scholarship,
            "verify_scholarship": self.verify_scholarship,
            "save_scholarship": self.save_scholarship,
            "find_duplicate_scholarship": self.find_duplicate_scholarship,
            "get_user_profile": self.get_user_profile,
            "evaluate_eligibility": self.evaluate_eligibility,
            "schedule_deadline_reminders": self.schedule_deadline_reminders,
        }

    async def run(self, user_id: UUID, max_results: int = 10) -> AgentRun:
        run = AgentRun(
            user_id=user_id,
            agent_name="ScholarshipDiscoveryAgent",
            status=AgentRunStatus.RUNNING,
            started_at=utcnow(),
            input_payload={"user_id": str(user_id), "max_results": max_results},
        )
        self.db.add(run)
        await self.db.flush()

        discovered = 0
        saved = 0
        errors: list[str] = []
        queries: list[str] = []
        token_usage: dict[str, Any] = {"prompt_tokens": 0, "completion_tokens": 0, "estimated_cost": 0.0}

        try:
            profile_data = await self._call_tool(run, "get_user_profile", {"user_id": str(user_id)})
            if not profile_data.get("ok"):
                raise RuntimeError(profile_data.get("error") or "Profile not found")

            profile = profile_data["profile"]
            queries = self.gemini.generate_search_queries(profile, count=8)
            self._accumulate_usage(token_usage)
            run.search_queries = queries

            candidate_urls: list[dict[str, str]] = []
            for query in queries:
                search_out = await self._call_tool(
                    run, "search_web", {"query": query, "max_results": 5}
                )
                for item in search_out.get("results", []):
                    candidate_urls.append(item)
                if len(candidate_urls) >= max_results * 3:
                    break

            # Prefer official-looking URLs
            ranked = sorted(
                candidate_urls,
                key=lambda x: classify_source(x.get("url", ""), x.get("title"))[1],
                reverse=True,
            )
            seen_urls: set[str] = set()
            for item in ranked:
                if saved >= max_results:
                    break
                url = item.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                try:
                    page = await self._call_tool(run, "fetch_page", {"url": url})
                    if not page.get("ok"):
                        continue
                    extracted = await self._call_tool(
                        run,
                        "extract_scholarship",
                        {"url": page.get("final_url") or url, "html": page.get("html", "")},
                    )
                    if not extracted.get("ok") or not extracted.get("data"):
                        continue
                    discovered += 1
                    dup = await self._call_tool(
                        run, "find_duplicate_scholarship", {"data": extracted["data"]}
                    )
                    if dup.get("duplicate_id"):
                        # Attach source to existing
                        await self._attach_source(UUID(dup["duplicate_id"]), url, item.get("title"))
                        continue
                    saved_out = await self._call_tool(
                        run,
                        "save_scholarship",
                        {
                            "data": extracted["data"],
                            "source_url": url,
                            "content_hash": page.get("content_hash"),
                        },
                    )
                    if saved_out.get("scholarship_id"):
                        scholarship_id = UUID(saved_out["scholarship_id"])
                        saved += 1
                        await self._call_tool(
                            run,
                            "evaluate_eligibility",
                            {"user_id": str(user_id), "scholarship_id": str(scholarship_id)},
                        )
                        await self._call_tool(
                            run,
                            "schedule_deadline_reminders",
                            {"user_id": str(user_id), "scholarship_id": str(scholarship_id)},
                        )
                except Exception as exc:
                    logger.exception("Discovery item failed for %s", url)
                    errors.append(f"{url}: {exc}")

            run.status = AgentRunStatus.COMPLETED
            run.decision_summary = (
                f"Ran {len(queries)} queries, discovered {discovered} candidates, saved {saved}."
            )
        except Exception as exc:
            logger.exception("Discovery agent failed")
            run.status = AgentRunStatus.FAILED
            errors.append(str(exc))
            run.decision_summary = f"Failed: {exc}"

        run.finished_at = utcnow()
        run.scholarships_discovered = discovered
        run.scholarships_saved = saved
        run.errors = errors
        run.token_usage = token_usage
        run.estimated_api_cost = token_usage.get("estimated_cost")
        run.output_payload = {"discovered": discovered, "saved": saved}
        await self.db.flush()
        return run

    def _accumulate_usage(self, token_usage: dict[str, Any]) -> None:
        u = self.gemini.last_usage or {}
        token_usage["prompt_tokens"] += u.get("prompt_tokens", 0)
        token_usage["completion_tokens"] += u.get("completion_tokens", 0)
        token_usage["estimated_cost"] += u.get("estimated_cost", 0.0)

    async def _call_tool(self, run: AgentRun, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        success = True
        error_message = None
        # Avoid storing huge HTML in DB
        stored_input = {k: v for k, v in input_data.items() if k != "html"}
        if "html" in input_data:
            stored_input["html_length"] = len(input_data.get("html") or "")
        try:
            tool = self._tools[name]
            output = await tool(**input_data)
            if not isinstance(output, dict):
                output = {"result": output}
        except Exception as exc:
            success = False
            error_message = str(exc)
            output = {"ok": False, "error": str(exc)}
            logger.warning("Tool %s failed: %s", name, exc)

        duration_ms = int((time.perf_counter() - start) * 1000)
        # Truncate large outputs
        stored_output = output
        if isinstance(output, dict) and "html" in output:
            stored_output = {**output, "html": f"<truncated {len(output['html'])} chars>"}

        self.db.add(
            AgentToolCall(
                agent_run_id=run.id,
                tool_name=name,
                input_data=stored_input,
                output_data=stored_output if isinstance(stored_output, dict) else {"result": stored_output},
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
            )
        )
        await self.db.flush()
        return output

    # ---- Tools ----

    async def search_web(self, query: str, max_results: int = 10) -> dict[str, Any]:
        results = await self.search.search(query, max_results=max_results)
        return {
            "ok": True,
            "results": [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results],
        }

    async def fetch_page(self, url: str, html: str | None = None) -> dict[str, Any]:
        result = await self.scraper.fetch(url)
        return {
            "ok": True,
            "status_code": result.status_code,
            "html": result.html,
            "content_hash": result.content_hash,
            "final_url": result.final_url,
            "used_playwright": result.used_playwright,
        }

    async def render_dynamic_page(self, url: str) -> dict[str, Any]:
        result = await self.scraper.render_dynamic_page(url)
        return {
            "ok": True,
            "status_code": result.status_code,
            "html": result.html,
            "content_hash": result.content_hash,
            "final_url": result.final_url,
            "used_playwright": True,
        }

    async def extract_scholarship(self, url: str, html: str = "") -> dict[str, Any]:
        text = self.scraper.extract_text(html) if html else ""
        if not text:
            return {"ok": False, "error": "Empty page text"}
        if self.gemini.available:
            extraction = self.gemini.extract_scholarship(text, url)
            return {"ok": True, "data": extraction.model_dump(mode="json")}
        # Offline / no-key heuristic extraction from title-ish content
        return {
            "ok": True,
            "data": ScholarshipExtraction(
                name=text[:120].split(".")[0][:200] or None,
                source_url=url,
                official_url=url,
                confidence=0.2,
                fact_statuses={"name": FactStatus.UNVERIFIED},
                description=text[:500],
            ).model_dump(mode="json"),
        }

    async def verify_scholarship(self, url: str) -> dict[str, Any]:
        level, score, is_official = classify_source(url)
        return {
            "ok": True,
            "reliability_level": level.value,
            "trust_score": score,
            "is_official": is_official,
        }

    async def find_duplicate_scholarship(self, data: dict[str, Any]) -> dict[str, Any]:
        dup = await self.dedupe.find_duplicate(
            name=data.get("name"),
            provider=data.get("provider"),
            official_url=data.get("official_url") or data.get("source_url"),
            host_institution=data.get("host_institution"),
        )
        return {"ok": True, "duplicate_id": str(dup.id) if dup else None}

    async def save_scholarship(
        self,
        data: dict[str, Any],
        source_url: str,
        content_hash: str | None = None,
    ) -> dict[str, Any]:
        extraction = ScholarshipExtraction.model_validate(data)
        if not extraction.name:
            return {"ok": False, "error": "Cannot save scholarship without a name"}

        funding = extraction.funding
        if funding.fully_funded:
            funding_type = FundingType.FULLY_FUNDED
        elif funding.tuition:
            funding_type = FundingType.TUITION_ONLY
        elif funding.stipend:
            funding_type = FundingType.STIPEND_ONLY
        else:
            funding_type = FundingType.UNKNOWN

        official = extraction.official_url or source_url
        level, trust, is_official = classify_source(official or source_url)
        verification = (
            VerificationStatus.VERIFIED if is_official else VerificationStatus.UNVERIFIED
        )

        scholarship = Scholarship(
            name=extraction.name,
            provider=extraction.provider,
            description=extraction.description,
            official_url=official,
            normalized_url=normalize_url(official) if official else None,
            country=extraction.country,
            host_institution=extraction.host_institution,
            degree_levels=extraction.degree_levels,
            fields_of_study=extraction.fields_of_study,
            eligible_nationalities=extraction.eligible_nationalities,
            funding_type=funding_type,
            tuition_coverage=funding.tuition,
            stipend=funding.stipend,
            travel_coverage=funding.travel,
            insurance_coverage=funding.insurance,
            accommodation_coverage=funding.accommodation,
            application_open_date=extraction.application.opens,
            application_deadline=extraction.application.deadline,
            minimum_gpa=extraction.eligibility.minimum_gpa,
            required_degree=extraction.eligibility.degree_requirement,
            minimum_work_experience=extraction.eligibility.work_experience_years,
            language_requirements=extraction.eligibility.language_requirement,
            age_requirement=extraction.eligibility.age_limit,
            application_process="\n".join(extraction.application_steps) or None,
            source_reliability=level.value,
            verification_status=verification,
            last_verified_at=utcnow() if is_official else None,
            confidence=extraction.confidence,
            fact_statuses={k: (v.value if hasattr(v, "value") else v) for k, v in (extraction.fact_statuses or {}).items()},
            search_vector=" ".join(
                filter(
                    None,
                    [
                        extraction.name,
                        extraction.provider,
                        extraction.country,
                        " ".join(extraction.fields_of_study),
                    ],
                )
            ),
        )
        self.db.add(scholarship)
        await self.db.flush()

        self.db.add(
            ScholarshipSource(
                scholarship_id=scholarship.id,
                url=source_url,
                title=extraction.name,
                reliability_level=level.value,
                trust_score=trust,
                is_official=is_official,
                last_fetched_at=utcnow(),
                content_hash=content_hash,
            )
        )
        for doc in extraction.required_documents:
            self.db.add(
                ScholarshipDocument(
                    scholarship_id=scholarship.id,
                    name=doc,
                    is_required=True,
                    fact_status=FactStatus.UNVERIFIED,
                    source_url=source_url,
                )
            )
        for step in extraction.application_steps:
            self.db.add(
                ScholarshipRequirement(
                    scholarship_id=scholarship.id,
                    category="application_step",
                    description=step,
                    fact_status=FactStatus.UNVERIFIED,
                    source_url=source_url,
                )
            )
        await self.db.flush()
        return {"ok": True, "scholarship_id": str(scholarship.id)}

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        uid = UUID(user_id)
        result = await self.db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == uid)
        )
        user = result.scalar_one_or_none()
        if not user or not user.profile:
            return {"ok": False, "error": "User profile not found"}
        p: UserProfile = user.profile
        return {
            "ok": True,
            "profile": {
                "nationality": p.nationality,
                "country_of_residence": p.country_of_residence,
                "highest_degree": p.highest_degree,
                "target_degree": p.target_degree,
                "fields": p.fields or [],
                "graduation_year": p.graduation_year,
                "gpa": p.gpa,
                "english_tests": p.english_tests or {},
                "work_experience_years": p.work_experience_years,
                "preferred_countries": p.preferred_countries or [],
                "funding_preference": p.funding_preference,
                "age": p.age,
            },
        }

    async def evaluate_eligibility(self, user_id: str, scholarship_id: str) -> dict[str, Any]:
        from app.agents.eligibility_agent import EligibilityAgent

        agent = EligibilityAgent(self.db, self.gemini)
        match = await agent.evaluate(UUID(user_id), UUID(scholarship_id))
        return {"ok": True, "match_id": str(match.id), "status": match.status.value}

    async def schedule_deadline_reminders(self, user_id: str, scholarship_id: str) -> dict[str, Any]:
        from app.services.reminders import ReminderService

        user = (await self.db.execute(select(User).where(User.id == UUID(user_id)))).scalar_one()
        reminders = await ReminderService(self.db).schedule_for_scholarship(
            user, UUID(scholarship_id)
        )
        return {"ok": True, "reminders_created": len(reminders)}

    async def _attach_source(self, scholarship_id: UUID, url: str, title: str | None) -> None:
        level, trust, is_official = classify_source(url, title)
        existing = await self.db.execute(
            select(ScholarshipSource).where(
                ScholarshipSource.scholarship_id == scholarship_id,
                ScholarshipSource.url == url,
            )
        )
        if existing.scalar_one_or_none():
            return
        self.db.add(
            ScholarshipSource(
                scholarship_id=scholarship_id,
                url=url,
                title=title,
                reliability_level=level.value,
                trust_score=trust,
                is_official=is_official,
                last_fetched_at=utcnow(),
            )
        )
        await self.db.flush()
