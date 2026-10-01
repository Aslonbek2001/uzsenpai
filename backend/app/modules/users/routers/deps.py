"""Dependency wiring for this module's routers — the session is injected here, never in a route."""

from typing import Annotated

from fastapi import Depends

from app.core.db import SessionDep
from app.modules.users.services import ProfileService


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(session)


Profiles = Annotated[ProfileService, Depends(get_profile_service)]
