"""/api/v1/users/me — the signed-in user's own profile and onboarding answers."""

from fastapi import APIRouter

from app.modules.auth.public import CurrentUserDep
from app.modules.users.routers.deps import Deletions, Profiles
from app.modules.users.schemas import MeOut, MeUpdateIn

router = APIRouter(prefix="/me")


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUserDep, profiles: Profiles) -> MeOut:
    return await profiles.get_me(user.id)


@router.patch("", response_model=MeOut)
async def update_me(data: MeUpdateIn, user: CurrentUserDep, profiles: Profiles) -> MeOut:
    return await profiles.update_me(user.id, data)


@router.post("/delete", response_model=MeOut)
async def request_deletion(user: CurrentUserDep, deletions: Deletions) -> MeOut:
    """Signs out every device; the account can be restored by signing in within 30 days, then it's anonymized."""
    return await deletions.request(user.id)


@router.post("/restore", response_model=MeOut)
async def restore(user: CurrentUserDep, deletions: Deletions) -> MeOut:
    return await deletions.restore(user.id)
