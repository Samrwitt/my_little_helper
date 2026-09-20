from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import ProfileOut, ProfileUpdate
from app.services.auth import ProfileService
from app.agents.eligibility_agent import EligibilityAgent

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(user: CurrentUser, db: DbSession) -> ProfileOut:
    profile = await ProfileService(db).get_or_create(user)
    return ProfileOut.model_validate(profile)


@router.put("", response_model=ProfileOut)
async def update_profile(data: ProfileUpdate, user: CurrentUser, db: DbSession) -> ProfileOut:
    profile = await ProfileService(db).update(user, data)
    # Recompute eligibility when profile changes
    await EligibilityAgent(db).recompute_for_user(user.id)
    return ProfileOut.model_validate(profile)
