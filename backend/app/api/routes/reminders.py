from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import ReminderOut
from app.services.reminders import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
async def list_reminders(user: CurrentUser, db: DbSession) -> list[ReminderOut]:
    rows = await ReminderService(db).list_for_user(user)
    return [ReminderOut.model_validate(r) for r in rows]
