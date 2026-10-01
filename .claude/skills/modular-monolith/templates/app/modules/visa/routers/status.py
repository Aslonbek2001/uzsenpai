"""/api/v1/visa/status — thin: parse → service → schema."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.public import CurrentUser, current_user
from app.modules.visa.routers.deps import StatusService, Today
from app.modules.visa.schemas import VisaStatusIn, VisaStatusOut

router = APIRouter(prefix="/status")
User = Annotated[CurrentUser, Depends(current_user)]


@router.get("", response_model=VisaStatusOut)
async def get_status(user: User, service: StatusService, now: Today) -> VisaStatusOut:
    return await service.get(user.id, now)


@router.put("", response_model=VisaStatusOut)
async def save_status(data: VisaStatusIn, user: User, service: StatusService, now: Today) -> VisaStatusOut:
    return await service.save(user.id, data, now)
