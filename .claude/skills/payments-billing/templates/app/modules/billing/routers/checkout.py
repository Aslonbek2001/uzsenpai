from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.modules.auth.public import CurrentUser, current_user
from app.modules.billing.routers.deps import Checkout
from app.modules.billing.schemas import CheckoutIn, CheckoutOut
from app.shared.i18n import locale_from_request

router = APIRouter()
User = Annotated[CurrentUser, Depends(current_user)]


@router.post("/checkout", response_model=CheckoutOut, status_code=201)
async def start_checkout(data: CheckoutIn, user: User, service: Checkout, request: Request) -> CheckoutOut:
    return await service.start(user.id, data, locale_from_request(request))
