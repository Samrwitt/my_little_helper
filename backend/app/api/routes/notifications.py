from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas import NotificationOut
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user: CurrentUser,
    db: DbSession,
    unread_only: bool = Query(False),
) -> list[NotificationOut]:
    rows = await NotificationService(db).list_for_user(user, unread_only=unread_only)
    return [NotificationOut.model_validate(r) for r in rows]


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: UUID, user: CurrentUser, db: DbSession
) -> NotificationOut:
    n = await NotificationService(db).mark_read(user, notification_id)
    return NotificationOut.model_validate(n)
