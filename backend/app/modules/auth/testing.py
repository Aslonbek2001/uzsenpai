"""Factories other modules' TESTS may use: a real access token for a user (no HTTP sign-in needed)."""

import uuid

from app.modules.auth.services import issue_access_token
from app.modules.users.public import UserRole
from app.shared.ids import uuid7


def auth_headers_for(user_id: uuid.UUID, role: UserRole = UserRole.USER) -> dict[str, str]:
    token, _ = issue_access_token(user_id, role, uuid7())
    return {"Authorization": f"Bearer {token}"}
