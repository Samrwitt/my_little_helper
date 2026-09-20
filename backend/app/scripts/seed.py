"""Development seed data. Safe to re-run — skips if demo user exists."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.enums import (
    ApplicationStatus,
    EligibilityStatus,
    FactStatus,
    FundingType,
    NotificationChannel,
    ReminderType,
    VerificationStatus,
)
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models import (
    Application,
    ApplicationDocument,
    Notification,
    Reminder,
    Scholarship,
    ScholarshipDocument,
    ScholarshipMatch,
    ScholarshipSource,
    User,
    UserProfile,
)


SCHOLARSHIPS = [
    {
        "name": "Erasmus Mundus Joint Masters — AI for Society",
        "provider": "European Commission",
        "description": "Fully funded joint masters across European universities focusing on artificial intelligence applications for society.",
        "official_url": "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en",
        "country": "Europe",
        "host_institution": "Consortium of EU Universities",
        "degree_levels": ["Masters"],
        "fields_of_study": ["Artificial Intelligence", "Computer Science", "Data Science"],
        "eligible_nationalities": ["international", "Ethiopian"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "EUR 1400/month",
        "travel_coverage": True,
        "insurance_coverage": True,
        "accommodation_coverage": False,
        "application_deadline": date(2027, 1, 12),
        "minimum_gpa": 3.0,
        "required_degree": "Bachelor's in related field",
        "language_requirements": "IELTS 6.5 or equivalent",
        "documents": ["CV", "Transcript", "Motivation Letter", "Recommendation Letter 1", "Recommendation Letter 2", "Passport", "IELTS"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "DAAD EPOS Scholarship",
        "provider": "DAAD",
        "description": "Development-related postgraduate courses for professionals from developing countries.",
        "official_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
        "country": "Germany",
        "host_institution": "German Universities",
        "degree_levels": ["Masters", "PhD"],
        "fields_of_study": ["Computer Science", "Engineering", "Data Science"],
        "eligible_nationalities": ["Ethiopian", "developing countries"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "EUR 934/month",
        "travel_coverage": True,
        "insurance_coverage": True,
        "accommodation_coverage": False,
        "application_deadline": date(2026, 10, 15),
        "minimum_gpa": 3.0,
        "required_degree": "Bachelor's with 2+ years work experience",
        "minimum_work_experience": 2.0,
        "language_requirements": "English or German proficiency",
        "documents": ["CV", "Transcript", "Motivation Letter", "Recommendation Letter", "Proof of Employment", "Passport"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "ETH Zurich Excellence Scholarship",
        "provider": "ETH Zurich",
        "description": "Merit-based scholarship covering living and study costs for master's students at ETH Zurich.",
        "official_url": "https://ethz.ch/en/studies/financial/scholarships/excellencescholarship.html",
        "country": "Switzerland",
        "host_institution": "ETH Zurich",
        "degree_levels": ["Masters"],
        "fields_of_study": ["Computer Science", "Machine Learning", "Engineering"],
        "eligible_nationalities": ["international"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "CHF 12,000/semester",
        "travel_coverage": False,
        "insurance_coverage": False,
        "accommodation_coverage": False,
        "application_deadline": date(2026, 12, 15),
        "minimum_gpa": 3.5,
        "required_degree": "Bachelor's",
        "language_requirements": "English proficiency",
        "documents": ["CV", "Transcript", "Motivation Letter", "Recommendation Letter 1", "Recommendation Letter 2"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "University of Oxford Reach Oxford Scholarship",
        "provider": "University of Oxford",
        "description": "Full scholarship for undergraduate students from low-income countries. Listed for reference alongside postgraduate options.",
        "official_url": "https://www.ox.ac.uk/admissions/undergraduate/fees-and-funding/oxford-support/reach-oxford-scholarship",
        "country": "United Kingdom",
        "host_institution": "University of Oxford",
        "degree_levels": ["Bachelors"],
        "fields_of_study": ["Computer Science", "Engineering", "Mathematics"],
        "eligible_nationalities": ["Ethiopian", "developing countries"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "Living costs covered",
        "travel_coverage": True,
        "insurance_coverage": False,
        "accommodation_coverage": True,
        "application_deadline": date(2027, 2, 1),
        "minimum_gpa": 3.7,
        "required_degree": "Secondary school leaving certificate",
        "language_requirements": "IELTS 7.0",
        "documents": ["CV", "Transcript", "Personal Statement", "Recommendation Letter", "Passport", "IELTS"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "Chevening Scholarship",
        "provider": "UK Foreign, Commonwealth & Development Office",
        "description": "UK government's global scholarship programme for one-year master's degrees.",
        "official_url": "https://www.chevening.org/scholarships/",
        "country": "United Kingdom",
        "host_institution": "UK Universities",
        "degree_levels": ["Masters"],
        "fields_of_study": ["Computer Science", "Artificial Intelligence", "Public Policy", "Data Science"],
        "eligible_nationalities": ["Ethiopian", "eligible countries"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "Monthly living allowance",
        "travel_coverage": True,
        "insurance_coverage": False,
        "accommodation_coverage": False,
        "application_deadline": date(2026, 11, 5),
        "minimum_gpa": 3.0,
        "required_degree": "Bachelor's",
        "minimum_work_experience": 2.0,
        "language_requirements": "IELTS or equivalent",
        "documents": ["CV", "Transcript", "Essays", "Recommendation Letter 1", "Recommendation Letter 2", "IELTS"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "Fulbright Foreign Student Program",
        "provider": "U.S. Department of State",
        "description": "Graduate study funding for international students at U.S. universities.",
        "official_url": "https://foreign.fulbrightonline.org/",
        "country": "United States",
        "host_institution": "U.S. Universities",
        "degree_levels": ["Masters", "PhD"],
        "fields_of_study": ["Computer Science", "Engineering", "Arts", "Sciences"],
        "eligible_nationalities": ["Ethiopian", "international"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "Monthly stipend",
        "travel_coverage": True,
        "insurance_coverage": True,
        "accommodation_coverage": False,
        "application_deadline": date(2026, 5, 15),
        "minimum_gpa": 3.0,
        "required_degree": "Bachelor's",
        "language_requirements": "TOEFL required",
        "documents": ["CV", "Transcript", "Personal Statement", "Recommendation Letters", "TOEFL", "Passport"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "Sweden Institute Scholarships for Global Professionals",
        "provider": "Swedish Institute",
        "description": "Fully funded master's scholarships for global professionals.",
        "official_url": "https://si.se/en/apply/scholarships/swedish-institute-scholarships-for-global-professionals/",
        "country": "Sweden",
        "host_institution": "Swedish Universities",
        "degree_levels": ["Masters"],
        "fields_of_study": ["Computer Science", "Data Science", "Sustainable Development"],
        "eligible_nationalities": ["Ethiopian", "eligible countries"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "SEK 12,000/month",
        "travel_coverage": True,
        "insurance_coverage": True,
        "accommodation_coverage": False,
        "application_deadline": date(2027, 2, 18),
        "minimum_gpa": 3.0,
        "required_degree": "Bachelor's with work experience",
        "minimum_work_experience": 3.0,
        "language_requirements": "English proficiency",
        "documents": ["CV", "Transcript", "Motivation Letter", "Recommendation Letter", "Proof of Work", "Passport"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "Gates Cambridge Scholarship",
        "provider": "Bill & Melinda Gates Foundation",
        "description": "Full-cost scholarships for outstanding applicants from outside the UK to pursue postgraduate study at Cambridge.",
        "official_url": "https://www.gatescambridge.org/",
        "country": "United Kingdom",
        "host_institution": "University of Cambridge",
        "degree_levels": ["Masters", "PhD"],
        "fields_of_study": ["Computer Science", "Artificial Intelligence", "Sciences", "Humanities"],
        "eligible_nationalities": ["international"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "Maintenance allowance",
        "travel_coverage": True,
        "insurance_coverage": False,
        "accommodation_coverage": False,
        "application_deadline": date(2026, 12, 3),
        "minimum_gpa": 3.7,
        "required_degree": "Bachelor's",
        "language_requirements": "IELTS / TOEFL as required by course",
        "documents": ["CV", "Transcript", "Research Proposal", "Recommendation Letters", "Personal Statement"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
    {
        "name": "Holland Scholarship",
        "provider": "Dutch Ministry of Education",
        "description": "Scholarship for non-EEA students starting bachelor's or master's programmes in the Netherlands.",
        "official_url": "https://www.studyinholland.nl/finances/holland-scholarship",
        "country": "Netherlands",
        "host_institution": "Dutch Research Universities / Universities of Applied Sciences",
        "degree_levels": ["Bachelors", "Masters"],
        "fields_of_study": ["Computer Science", "Engineering", "Data Science"],
        "eligible_nationalities": ["international", "non-EEA"],
        "funding_type": FundingType.PARTIAL,
        "tuition_coverage": False,
        "stipend": "EUR 5,000 one-time",
        "travel_coverage": False,
        "insurance_coverage": False,
        "accommodation_coverage": False,
        "application_deadline": date(2027, 5, 1),
        "minimum_gpa": None,
        "required_degree": "Depends on programme",
        "language_requirements": "English proficiency",
        "documents": ["CV", "Transcript", "Motivation Letter", "Admission Letter"],
        "verification_status": VerificationStatus.UNVERIFIED,
        "source_reliability": 2,
    },
    {
        "name": "Mastercard Foundation Scholars Program",
        "provider": "Mastercard Foundation",
        "description": "Comprehensive scholarships for academically talented young people from Africa.",
        "official_url": "https://mastercardfdn.org/en/programs/scholars/",
        "country": "Multiple",
        "host_institution": "Partner Universities",
        "degree_levels": ["Bachelors", "Masters"],
        "fields_of_study": ["Computer Science", "Engineering", "Agriculture", "Health"],
        "eligible_nationalities": ["Ethiopian", "African"],
        "funding_type": FundingType.FULLY_FUNDED,
        "tuition_coverage": True,
        "stipend": "Living stipend",
        "travel_coverage": True,
        "insurance_coverage": True,
        "accommodation_coverage": True,
        "application_deadline": date(2026, 12, 31),
        "minimum_gpa": 3.0,
        "required_degree": "Varies by partner",
        "language_requirements": "Program dependent",
        "documents": ["CV", "Transcript", "Essays", "Recommendation Letters", "Passport"],
        "verification_status": VerificationStatus.VERIFIED,
        "source_reliability": 1,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == "demo@scholarship.local"))
        if existing.scalar_one_or_none():
            print("Seed data already present — skipping.")
            return

        user = User(
            id=uuid4(),
            email="demo@scholarship.local",
            hashed_password=hash_password("DemoPass123!"),
            full_name="Demo Student",
            is_active=True,
            is_verified=True,
            onboarding_completed=True,
        )
        db.add(user)
        await db.flush()

        profile = UserProfile(
            user_id=user.id,
            nationality="Ethiopian",
            country_of_residence="Ethiopia",
            highest_degree="BSc Computer Science",
            target_degree="Masters",
            fields=["Computer Science", "Artificial Intelligence", "Machine Learning", "Data Science"],
            graduation_year=2025,
            gpa=3.5,
            english_tests={"ielts": None, "toefl": None},
            work_experience_years=2,
            preferred_countries=[],
            funding_preference="fully-funded",
            age=24,
        )
        db.add(profile)

        scholarship_rows: list[Scholarship] = []
        for item in SCHOLARSHIPS:
            docs = item.pop("documents")
            s = Scholarship(
                id=uuid4(),
                fact_statuses={
                    "deadline": FactStatus.VERIFIED.value,
                    "funding": FactStatus.VERIFIED.value,
                    "eligible_nationalities": FactStatus.VERIFIED.value,
                },
                confidence=0.9,
                last_verified_at=utcnow(),
                application_year=2027,
                is_active=True,
                **item,
            )
            # restore documents key was popped
            db.add(s)
            await db.flush()
            db.add(
                ScholarshipSource(
                    scholarship_id=s.id,
                    url=s.official_url or "https://example.com",
                    title=s.name,
                    reliability_level=s.source_reliability,
                    trust_score=1.0 if s.source_reliability == 1 else 0.8,
                    is_official=s.source_reliability == 1,
                    last_fetched_at=utcnow(),
                )
            )
            for doc_name in docs:
                db.add(
                    ScholarshipDocument(
                        scholarship_id=s.id,
                        name=doc_name,
                        is_required=True,
                        fact_status=FactStatus.VERIFIED,
                        source_url=s.official_url,
                    )
                )
            scholarship_rows.append(s)

        await db.flush()

        # Matches for demo user
        match_specs = [
            (0, EligibilityStatus.LIKELY_ELIGIBLE, 0.78, ["Ethiopian applicants accepted", "Masters accepted", "CS field eligible", "GPA satisfied"], ["IELTS score", "2 recommendation letters"], [], ["Age requirement not specified"]),
            (1, EligibilityStatus.LIKELY_ELIGIBLE, 0.82, ["Ethiopian applicants accepted", "Work experience met", "GPA satisfied"], ["Motivation letter"], [], []),
            (2, EligibilityStatus.LIKELY_ELIGIBLE, 0.7, ["GPA requirement satisfied", "CS field eligible"], ["2 recommendation letters"], [], ["Language requirement details"]),
            (4, EligibilityStatus.LIKELY_ELIGIBLE, 0.75, ["Work experience met", "Degree accepted"], ["IELTS", "Essays"], [], []),
            (6, EligibilityStatus.UNCERTAIN, 0.45, ["Nationality eligible"], ["3 years work experience preferred"], [], ["Exact partner criteria"]),
            (7, EligibilityStatus.UNCERTAIN, 0.5, ["International students accepted"], ["Research proposal"], [], ["Competitiveness unknown"]),
            (9, EligibilityStatus.LIKELY_ELIGIBLE, 0.8, ["Ethiopian / African eligible", "CS field"], ["Essays"], [], []),
        ]

        for idx, status, conf, matched, missing, failed, unknown in match_specs:
            s = scholarship_rows[idx]
            db.add(
                ScholarshipMatch(
                    user_id=user.id,
                    scholarship_id=s.id,
                    status=status,
                    matched_requirements=matched,
                    missing_requirements=missing,
                    failed_requirements=failed,
                    unknown_requirements=unknown,
                    reasoning_summary=f"Heuristic match for {s.name}",
                    confidence=conf,
                    evaluated_at=utcnow(),
                )
            )

        # Applications across pipeline stages
        app_stages = [
            (0, ApplicationStatus.SAVED, 0),
            (1, ApplicationStatus.SAVED, 0),
            (2, ApplicationStatus.PREPARING, 40),
            (4, ApplicationStatus.APPLIED, 100),
            (7, ApplicationStatus.READY_TO_APPLY, 85),
            (9, ApplicationStatus.PREPARING, 28),
        ]
        for idx, status, readiness in app_stages:
            s = scholarship_rows[idx]
            app = Application(
                user_id=user.id,
                scholarship_id=s.id,
                status=status,
                readiness_percent=float(readiness),
                submitted_at=utcnow() if status == ApplicationStatus.APPLIED else None,
            )
            db.add(app)
            await db.flush()
            docs = (
                await db.execute(
                    select(ScholarshipDocument).where(ScholarshipDocument.scholarship_id == s.id)
                )
            ).scalars().all()
            for i, d in enumerate(docs):
                complete = readiness >= ((i + 1) / max(len(docs), 1) * 100)
                if status == ApplicationStatus.APPLIED:
                    complete = True
                db.add(
                    ApplicationDocument(
                        application_id=app.id,
                        name=d.name,
                        scholarship_document_id=d.id,
                        is_complete=complete,
                    )
                )

        # Reminders
        for idx in [0, 1, 2]:
            s = scholarship_rows[idx]
            if not s.application_deadline:
                continue
            days = (s.application_deadline - date.today()).days
            for d in [60, 30, 14, 7]:
                if days >= d:
                    remind_date = s.application_deadline - timedelta(days=d)
                    db.add(
                        Reminder(
                            user_id=user.id,
                            scholarship_id=s.id,
                            reminder_type=ReminderType.DEADLINE,
                            days_before=d,
                            scheduled_for=datetime.combine(
                                remind_date, datetime.min.time(), tzinfo=timezone.utc
                            ),
                            title=f"{s.name} — {d} days remaining",
                            message=f"Deadline {s.application_deadline.isoformat()}",
                            sent=False,
                            cancelled=False,
                        )
                    )

        db.add(
            Notification(
                user_id=user.id,
                channel=NotificationChannel.IN_APP,
                title="Welcome to Scholarship Autopilot",
                body="Your profile is ready. We matched several scholarships for you.",
                link="/dashboard",
                is_read=False,
            )
        )
        db.add(
            Notification(
                user_id=user.id,
                channel=NotificationChannel.IN_APP,
                title="Deadline approaching",
                body="DAAD EPOS Scholarship deadline is within 60 days. Start gathering documents.",
                link="/scholarships",),
                is_read=False,
            )
        )

        await db.commit()
        print("Seed complete.")
        print("  Demo login: demo@scholarship.local / DemoPass123!")


if __name__ == "__main__":
    asyncio.run(seed())
