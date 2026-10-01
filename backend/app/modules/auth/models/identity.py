import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_check, str_enum
from app.modules.auth.domain.enums import AuthProvider
from app.shared.ids import uuid7


class Identity(Base):
    """One way a user signs in. A user links several (Telegram + email + Google), at most one per provider."""

    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject"),  # one Telegram account / email / Google account → one user
        UniqueConstraint("user_id", "provider"),  # one identity per provider per user
        enum_check("provider", AuthProvider),
        CheckConstraint("provider = 'email' OR password_hash IS NULL", name="password_only_for_email"),
        CheckConstraint("provider <> 'email' OR subject = lower(subject)", name="email_subject_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    # FK into the users module — allowed for auth → users only (ADR 0008)
    # (no separate index: UNIQUE(user_id, provider) already starts with user_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users_users.id", ondelete="CASCADE"))
    provider: Mapped[AuthProvider] = mapped_column(str_enum(AuthProvider))
    subject: Mapped[str] = mapped_column(String(320))
    email: Mapped[str | None] = mapped_column(String(320))  # contact email from email / Google identities
    password_hash: Mapped[str | None] = mapped_column(String(255))  # argon2id, email provider only
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # email confirmed
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
