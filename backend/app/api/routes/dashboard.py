from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import DashboardOut
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
async def dashboard(user: CurrentUser, db: DbSession) -> DashboardOut:
    return await DashboardService(db).get_dashboard(user)
