import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, func, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_check, str_enum
from app.modules.auth.domain.enums import SessionRevokeReason
from app.shared.ids import uuid7


class Session(Base):
    """One refresh token. Rotation creates a new row in the same `family_id` (= one device / login) and marks
    this one `rotated`. If a rotated token is ever presented again, the whole family is revoked."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        enum_check("revoke_reason", SessionRevokeReason),
        CheckConstraint("(revoked_at IS NULL) = (revoke_reason IS NULL)", name="revoked_consistent"),
        # "Devices" list and logout-all: the live head of every family of a user
        Index("ix_auth_sessions_active", "user_id", postgresql_where=text("revoked_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users_users.id", ondelete="CASCADE"))  # ADR 0008
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)  # SHA-256 of the refresh token
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[SessionRevokeReason | None] = mapped_column(str_enum(SessionRevokeReason))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip: Mapped[IPv4Address | IPv6Address | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
