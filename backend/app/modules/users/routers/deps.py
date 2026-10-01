"""Dependency wiring for this module's routers — the session is injected here, never in a route."""

from typing import Annotated

from fastapi import Depends

from app.core.db import SessionDep
from app.modules.users.services import DeletionService, ProfileService


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(session)


def get_deletion_service(session: SessionDep) -> DeletionService:
    return DeletionService(session)


Profiles = Annotated[ProfileService, Depends(get_profile_service)]
Deletions = Annotated[DeletionService, Depends(get_deletion_service)]
