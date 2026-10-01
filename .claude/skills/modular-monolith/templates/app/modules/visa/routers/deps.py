"""Dependency wiring for this module's routers — the session is injected here, never in a route."""

from datetime import date
from typing import Annotated

from fastapi import Depends

from app.core.db import SessionDep
from app.modules.visa.services import VisaStatusService


def get_status_service(session: SessionDep) -> VisaStatusService:
    return VisaStatusService(session)


def today() -> date:  # overridable in tests via app.dependency_overrides
    return date.today()


StatusService = Annotated[VisaStatusService, Depends(get_status_service)]
Today = Annotated[date, Depends(today)]
