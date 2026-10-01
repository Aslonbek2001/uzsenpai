from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.public import CurrentUser, current_user
from app.modules.billing.routers.deps import Entitlements
from app.modules.billing.schemas import EntitlementsOut

router = APIRouter()
User = Annotated[CurrentUser, Depends(current_user)]


@router.get("/entitlements", response_model=EntitlementsOut)
async def my_entitlements(user: User, service: Entitlements) -> EntitlementsOut:
    return EntitlementsOut(keys=await service.keys(user.id))
