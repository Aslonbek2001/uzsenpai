"""/api/v1/users/me — the signed-in user's own profile and onboarding answers."""

from fastapi import APIRouter

from app.modules.auth.public import CurrentUserDep
from app.modules.users.routers.deps import Profiles
from app.modules.users.schemas import MeOut, MeUpdateIn

router = APIRouter(prefix="/me")


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUserDep, profiles: Profiles) -> MeOut:
    return await profiles.get_me(user.id)


@router.patch("", response_model=MeOut)
async def update_me(data: MeUpdateIn, user: CurrentUserDep, profiles: Profiles) -> MeOut:
    return await profiles.update_me(user.id, data)
