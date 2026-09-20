from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.config import get_settings
from app.core.enums import EligibilityStatus, FactStatus
from app.schemas import EligibilityEvaluation, ScholarshipExtraction

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a scholarship information extraction engine.
Extract ONLY facts explicitly present in the provided page text.
Never invent or guess missing information — use null / empty lists.
For each major field, set fact_statuses to verified (explicitly stated),
unverified (implied but not clear), or unknown (not present).
Return strict JSON matching the schema."""

ELIGIBILITY_SYSTEM = """You are a scholarship eligibility analyst.
Compare the user profile against scholarship requirements.
If scholarship requirements are incomplete, do NOT claim definitive eligibility —
prefer uncertain / likely_* statuses.
Never invent scholarship requirements.
Return strict JSON matching the schema."""


class GeminiService:
    """Central Gemini API wrapper. Do not call Gemini elsewhere."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None
        self.last_usage: dict[str, Any] = {}

    @property
    def available(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def _get_model(self):
        if self._model is not None:
            return self._model
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        import google.generativeai as genai

        genai.configure(api_key=self.settings.gemini_api_key)
        self._model = genai.GenerativeModel(self.settings.gemini_model)
        return self._model

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # Rough flash pricing estimate (USD) — informational only
        return (prompt_tokens * 0.0000001) + (completion_tokens * 0.0000004)

    def _record_usage(self, response: Any) -> None:
        usage = getattr(response, "usage_metadata", None)
        prompt = getattr(usage, "prompt_token_count", 0) or 0
        completion = getattr(usage, "candidates_token_count", 0) or 0
        self.last_usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "estimated_cost": self._estimate_cost(prompt, completion),
        }

    def _generate_json(self, system: str, user_prompt: str) -> dict[str, Any]:
        model = self._get_model()
        response = model.generate_content(
            [system, user_prompt],
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        )
        self._record_usage(response)
        text = response.text or "{}"
        return json.loads(text)

    def extract_scholarship(self, page_text: str, source_url: str) -> ScholarshipExtraction:
        prompt = (
            f"Source URL: {source_url}\n\n"
            f"Page text:\n{page_text[:40000]}\n\n"
            "Extract scholarship details as JSON with keys: "
            "name, provider, official_url, country, host_institution, degree_levels, "
            "fields_of_study, eligible_nationalities, funding, application, eligibility, "
            "required_documents, application_steps, description, source_url, confidence, fact_statuses."
        )
        data = self._generate_json(EXTRACTION_SYSTEM, prompt)
        data["source_url"] = data.get("source_url") or source_url
        # Normalize fact statuses
        facts = data.get("fact_statuses") or {}
        normalized = {}
        for k, v in facts.items():
            try:
                normalized[k] = FactStatus(v).value if not isinstance(v, FactStatus) else v.value
            except Exception:
                normalized[k] = FactStatus.UNKNOWN.value
        data["fact_statuses"] = normalized
        return ScholarshipExtraction.model_validate(data)

    def generate_search_queries(self, profile: dict[str, Any], count: int = 8) -> list[str]:
        if not self.available:
            return self._fallback_queries(profile, count)
        prompt = (
            "Generate scholarship web search queries for this student profile. "
            f"Return JSON: {{\"queries\": [\"...\"]}} with {count} diverse queries.\n"
            f"Profile: {json.dumps(profile)}\n"
            "Include nationality, degree, fields, funding preference, destination, and known programs "
            "(DAAD, Erasmus Mundus, Chevening, Fulbright) where relevant."
        )
        try:
            data = self._generate_json(
                "You generate precise scholarship search queries. Return JSON only.",
                prompt,
            )
            queries = data.get("queries") or []
            return [q for q in queries if isinstance(q, str)][:count]
        except Exception:
            logger.exception("generate_search_queries failed; using fallback")
            return self._fallback_queries(profile, count)

    def evaluate_eligibility(
        self, profile: dict[str, Any], scholarship: dict[str, Any]
    ) -> EligibilityEvaluation:
        if not self.available:
            return self._heuristic_eligibility(profile, scholarship)
        prompt = (
            f"User profile:\n{json.dumps(profile, default=str)}\n\n"
            f"Scholarship:\n{json.dumps(scholarship, default=str)}\n\n"
            "Return JSON with status, matched_requirements, missing_requirements, "
            "failed_requirements, unknown_requirements, reasoning_summary, confidence."
        )
        try:
            data = self._generate_json(ELIGIBILITY_SYSTEM, prompt)
            return EligibilityEvaluation.model_validate(data)
        except Exception:
            logger.exception("evaluate_eligibility Gemini failed; using heuristic")
            return self._heuristic_eligibility(profile, scholarship)

    def compare_scholarship_versions(
        self, previous: dict[str, Any], current: dict[str, Any]
    ) -> list[dict[str, Any]]:
        if not self.available:
            return self._diff_versions(previous, current)
        prompt = (
            "Compare previous and current scholarship records. "
            "Return JSON {\"changes\": [{\"field\":..., \"change_type\":..., \"previous\":..., \"new\":..., \"summary\":...}]}. "
            "Only include real differences.\n"
            f"Previous: {json.dumps(previous, default=str)}\n"
            f"Current: {json.dumps(current, default=str)}"
        )
        try:
            data = self._generate_json(
                "You detect scholarship data changes. Never invent differences.",
                prompt,
            )
            return data.get("changes") or []
        except Exception:
            return self._diff_versions(previous, current)

    def summarize_requirements(self, scholarship: dict[str, Any]) -> str:
        docs = scholarship.get("required_documents") or []
        reqs = scholarship.get("requirements") or []
        parts = []
        if docs:
            parts.append("Documents: " + ", ".join(docs))
        if reqs:
            parts.append("Requirements: " + "; ".join(str(r) for r in reqs))
        return " | ".join(parts) if parts else "No requirements extracted."

    def _fallback_queries(self, profile: dict[str, Any], count: int) -> list[str]:
        nationality = profile.get("nationality") or "international"
        degree = profile.get("target_degree") or "masters"
        fields = profile.get("fields") or ["computer science"]
        funding = profile.get("funding_preference") or "fully funded"
        year = (profile.get("graduation_year") or 2026) + 1
        countries = profile.get("preferred_countries") or []
        queries = []
        for field in fields[:3]:
            queries.append(f"{funding} {field} {degree} scholarships {year} international students")
            queries.append(f"{nationality} students {degree} scholarship {field}")
        queries.append(f"DAAD {fields[0]} scholarship")
        queries.append(f"Erasmus Mundus {fields[0]} scholarship")
        if countries:
            queries.append(f"{funding} {degree} scholarship {countries[0]} {fields[0]}")
        queries.append(f"fully funded data science masters scholarship Europe")
        # dedupe preserve order
        seen = set()
        out = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return out[:count]

    def _heuristic_eligibility(
        self, profile: dict[str, Any], scholarship: dict[str, Any]
    ) -> EligibilityEvaluation:
        matched: list[str] = []
        missing: list[str] = []
        failed: list[str] = []
        unknown: list[str] = []

        nationality = (profile.get("nationality") or "").lower()
        eligible_nats = [n.lower() for n in (scholarship.get("eligible_nationalities") or [])]
        if not eligible_nats:
            unknown.append("Eligible nationalities not specified")
        elif any(x in ("all", "international", "any") for x in eligible_nats) or nationality in eligible_nats:
            matched.append(f"{profile.get('nationality')} applicants accepted")
        else:
            # soft check — many lists are incomplete
            unknown.append("Nationality eligibility unclear from listed countries")

        target = (profile.get("target_degree") or "").lower()
        degrees = [d.lower() for d in (scholarship.get("degree_levels") or [])]
        if not degrees:
            unknown.append("Degree level not specified")
        elif any(target in d or d in target for d in degrees) or any(
            x in d for d in degrees for x in ("master", "msc", "ma")
        ):
            matched.append("Target degree level appears accepted")
        else:
            failed.append("Target degree may not match program levels")

        fields = [f.lower() for f in (profile.get("fields") or [])]
        sfields = [f.lower() for f in (scholarship.get("fields_of_study") or [])]
        if not sfields:
            unknown.append("Fields of study not specified")
        elif any(any(pf in sf or sf in pf for sf in sfields) for pf in fields):
            matched.append("Field of study appears eligible")
        else:
            unknown.append("Field of study match uncertain")

        min_gpa = scholarship.get("minimum_gpa")
        gpa = profile.get("gpa")
        if min_gpa is None:
            unknown.append("GPA requirement not specified")
        elif gpa is None:
            missing.append("GPA not provided in profile")
        elif float(gpa) >= float(min_gpa):
            matched.append("GPA requirement satisfied")
        else:
            failed.append("GPA below minimum requirement")

        lang = scholarship.get("language_requirements")
        tests = profile.get("english_tests") or {}
        if lang:
            if tests.get("ielts") or tests.get("toefl"):
                matched.append("English test score present in profile")
            else:
                missing.append("English language test score (IELTS/TOEFL)")
        else:
            unknown.append("Language requirement not specified")

        docs = scholarship.get("required_documents") or []
        for doc in docs:
            missing.append(doc)

        if failed:
            status = EligibilityStatus.LIKELY_INELIGIBLE
        elif missing and matched:
            status = EligibilityStatus.LIKELY_ELIGIBLE
        elif matched and not unknown:
            status = EligibilityStatus.LIKELY_ELIGIBLE
        elif not matched and unknown:
            status = EligibilityStatus.UNCERTAIN
        else:
            status = EligibilityStatus.UNCERTAIN

        # Never claim definitive eligible when unknowns remain
        if status == EligibilityStatus.ELIGIBLE and unknown:
            status = EligibilityStatus.LIKELY_ELIGIBLE

        confidence = 0.4 + 0.1 * len(matched) - 0.05 * len(unknown) - 0.15 * len(failed)
        confidence = max(0.1, min(0.85, confidence))

        summary = (
            f"Status: {status.value}. Matched {len(matched)}, missing {len(missing)}, "
            f"failed {len(failed)}, unknown {len(unknown)}."
        )
        return EligibilityEvaluation(
            status=status,
            matched_requirements=matched,
            missing_requirements=missing,
            failed_requirements=failed,
            unknown_requirements=unknown,
            reasoning_summary=summary,
            confidence=confidence,
        )

    def _diff_versions(
        self, previous: dict[str, Any], current: dict[str, Any]
    ) -> list[dict[str, Any]]:
        fields = [
            ("application_deadline", "deadline_changed"),
            ("eligible_nationalities", "eligible_countries_changed"),
            ("funding_type", "funding_changed"),
            ("tuition_coverage", "funding_changed"),
            ("stipend", "funding_changed"),
            ("minimum_gpa", "requirements_changed"),
            ("language_requirements", "requirements_changed"),
            ("required_degree", "requirements_changed"),
        ]
        changes = []
        for field, ctype in fields:
            old = previous.get(field)
            new = current.get(field)
            if old != new:
                changes.append(
                    {
                        "field": field,
                        "change_type": ctype,
                        "previous": old,
                        "new": new,
                        "summary": f"{field} changed from {old} to {new}",
                    }
                )
        return changes
