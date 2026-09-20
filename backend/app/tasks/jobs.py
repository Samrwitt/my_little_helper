from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _session():
    from app.db.session import AsyncSessionLocal

    return AsyncSessionLocal()


@celery_app.task(name="app.tasks.jobs.discover_scholarships_task")
def discover_scholarships_task(user_id: str, max_results: int = 10) -> dict:
    return run_async(_discover(user_id, max_results))


async def _discover(user_id: str, max_results: int) -> dict:
    from app.agents.discovery_agent import ScholarshipDiscoveryAgent

    async with await _session() as db:
        agent = ScholarshipDiscoveryAgent(db)
        run = await agent.run(UUID(user_id), max_results=max_results)
        await db.commit()
        return {
            "run_id": str(run.id),
            "status": run.status.value,
            "saved": run.scholarships_saved,
            "discovered": run.scholarships_discovered,
        }


@celery_app.task(name="app.tasks.jobs.discover_all_users")
def discover_all_users() -> dict:
    return run_async(_discover_all())


async def _discover_all() -> dict:
    from app.models import User

    async with await _session() as db:
        users = (
            await db.execute(select(User).where(User.onboarding_completed.is_(True), User.is_active.is_(True)))
        ).scalars().all()
        queued = 0
        for u in users:
            discover_scholarships_task.delay(str(u.id), 5)
            queued += 1
        return {"queued": queued}


@celery_app.task(name="app.tasks.jobs.refresh_scholarship")
def refresh_scholarship(scholarship_id: str) -> dict:
    return run_async(_refresh(scholarship_id))


async def _refresh(scholarship_id: str) -> dict:
    from app.services.refresh import ScholarshipRefreshService

    async with await _session() as db:
        changes = await ScholarshipRefreshService(db).refresh(UUID(scholarship_id))
        await db.commit()
        return {"changes": len(changes)}


@celery_app.task(name="app.tasks.jobs.verify_deadline")
def verify_deadline(scholarship_id: str) -> dict:
    return refresh_scholarship(scholarship_id)


@celery_app.task(name="app.tasks.jobs.check_changed_requirements")
def check_changed_requirements(scholarship_id: str) -> dict:
    return refresh_scholarship(scholarship_id)


@celery_app.task(name="app.tasks.jobs.evaluate_user_matches")
def evaluate_user_matches(user_id: str) -> dict:
    return run_async(_evaluate_user(user_id))


async def _evaluate_user(user_id: str) -> dict:
    from app.agents.eligibility_agent import EligibilityAgent

    async with await _session() as db:
        count = await EligibilityAgent(db).recompute_for_user(UUID(user_id))
        await db.commit()
        return {"evaluated": count}


@celery_app.task(name="app.tasks.jobs.send_deadline_reminders")
def send_deadline_reminders() -> dict:
    return run_async(_send_reminders())


async def _send_reminders() -> dict:
    from app.models import Reminder, User
    from app.services.notifications import NotificationService
    from app.services.reminders import ReminderService

    async with await _session() as db:
        due = await ReminderService(db).due_reminders()
        notifier = NotificationService(db)
        sent = 0
        for reminder in due:
            user = (await db.execute(select(User).where(User.id == reminder.user_id))).scalar_one()
            link = f"/scholarships/{reminder.scholarship_id}" if reminder.scholarship_id else None
            await notifier.create_and_send(
                user,
                title=reminder.title,
                body=reminder.message,
                link=link,
            )
            reminder.sent = True
            sent += 1
        await db.commit()
        return {"sent": sent}


@celery_app.task(name="app.tasks.jobs.verify_all_scholarships")
def verify_all_scholarships() -> dict:
    return run_async(_verify_all())


async def _verify_all() -> dict:
    from app.models import Scholarship

    async with await _session() as db:
        rows = (
            await db.execute(select(Scholarship).where(Scholarship.is_active.is_(True)).limit(100))
        ).scalars().all()
        for s in rows:
            refresh_scholarship.delay(str(s.id))
        return {"queued": len(rows)}


@celery_app.task(name="app.tasks.jobs.recheck_approaching_scholarships")
def recheck_approaching_scholarships() -> dict:
    return run_async(_recheck_approaching())


async def _recheck_approaching() -> dict:
    from app.models import Scholarship

    async with await _session() as db:
        today = datetime.now(timezone.utc).date()
        cutoff = today + timedelta(days=30)
        rows = (
            await db.execute(
                select(Scholarship).where(
                    Scholarship.is_active.is_(True),
                    Scholarship.application_deadline >= today,
                    Scholarship.application_deadline <= cutoff,
                )
            )
        ).scalars().all()
        for s in rows:
            refresh_scholarship.delay(str(s.id))
        return {"queued": len(rows)}


@celery_app.task(name="app.tasks.jobs.remove_expired_opportunities")
def remove_expired_opportunities() -> dict:
    return run_async(_remove_expired())


async def _remove_expired() -> dict:
    from app.models import Scholarship

    async with await _session() as db:
        today = datetime.now(timezone.utc).date()
        grace = today - timedelta(days=14)
        rows = (
            await db.execute(
                select(Scholarship).where(
                    Scholarship.is_active.is_(True),
                    Scholarship.application_deadline < grace,
                )
            )
        ).scalars().all()
        for s in rows:
            s.is_active = False
        await db.commit()
        return {"deactivated": len(rows)}
