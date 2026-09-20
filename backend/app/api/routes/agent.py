from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models import AgentRun
from app.schemas import AgentRunOut, DiscoverRequest
from app.tasks.jobs import discover_scholarships_task

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/discover", response_model=AgentRunOut)
async def trigger_discover(
    data: DiscoverRequest,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> AgentRunOut:
    settings = get_settings()
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = (
        await db.execute(
            select(func.count())
            .select_from(AgentRun)
            .where(
                AgentRun.user_id == user.id,
                AgentRun.agent_name == "ScholarshipDiscoveryAgent",
                AgentRun.created_at >= since,
            )
        )
    ).scalar() or 0
    if count >= settings.discover_rate_limit_per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Discovery rate limit: {settings.discover_rate_limit_per_hour} per hour",
        )

    if not user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your profile before running discovery",
        )

    from app.agents.discovery_agent import ScholarshipDiscoveryAgent
    from app.core.enums import AgentRunStatus
    from app.db.base import utcnow
    from app.models import AgentRun as AgentRunModel

    # Prefer Celery when the broker is reachable; otherwise run inline.
    try:
        async_result = discover_scholarships_task.delay(str(user.id), data.max_results)
        run = AgentRunModel(
            user_id=user.id,
            agent_name="ScholarshipDiscoveryAgent",
            status=AgentRunStatus.PENDING,
            started_at=utcnow(),
            input_payload={
                "user_id": str(user.id),
                "max_results": data.max_results,
                "task_id": async_result.id,
            },
            decision_summary="Queued for background discovery",
        )
        db.add(run)
        await db.flush()
        return AgentRunOut.model_validate(run)
    except Exception:
        agent = ScholarshipDiscoveryAgent(db)
        run = await agent.run(user.id, max_results=data.max_results)
        return AgentRunOut.model_validate(run)


@router.get("/runs", response_model=list[AgentRunOut])
async def list_runs(user: CurrentUser, db: DbSession) -> list[AgentRunOut]:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(20)
    )
    return [AgentRunOut.model_validate(r) for r in result.scalars().all()]
