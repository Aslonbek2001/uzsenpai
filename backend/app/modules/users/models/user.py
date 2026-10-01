import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_check, str_enum
from app.modules.users.domain.enums import JlptLevel, UserGoal, UserRole, UserStatus
from app.modules.users.domain.rules import DEFAULT_TIMEZONE, DISPLAY_NAME_MAX
from app.shared.i18n import DEFAULT_LOCALE, Locale
from app.shared.ids import uuid7


class User(Base):
    """A person on the platform. Emails / Telegram ids live in auth_identities (one user, many sign-in methods)."""

    __tablename__ = "users_users"
    __table_args__ = (
        enum_check("locale", Locale),
        enum_check("role", UserRole),
        enum_check("status", UserStatus),
        enum_check("jlpt_level", JlptLevel),
        enum_check("goal", UserGoal),
        CheckConstraint("residence_country ~ '^[A-Z]{2}$'", name="residence_country"),  # ISO 3166-1 alpha-2
        # lifecycle timestamps always match the status
        CheckConstraint("(status = 'active') = (deletion_requested_at IS NULL)", name="deletion_requested_at"),
        CheckConstraint("(status = 'deleted') = (deleted_at IS NOT NULL)", name="deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX))
    locale: Mapped[Locale] = mapped_column(
        str_enum(Locale, length=5), default=DEFAULT_LOCALE, server_default=DEFAULT_LOCALE.value
    )
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole), default=UserRole.USER, server_default=UserRole.USER.value
    )
    status: Mapped[UserStatus] = mapped_column(
        str_enum(UserStatus), default=UserStatus.ACTIVE, server_default=UserStatus.ACTIVE.value
    )

    # Onboarding answers — all optional until the user completes onboarding
    residence_country: Mapped[str | None] = mapped_column(String(2))
    timezone: Mapped[str] = mapped_column(String(64), default=DEFAULT_TIMEZONE, server_default=DEFAULT_TIMEZONE)
    jlpt_level: Mapped[JlptLevel | None] = mapped_column(str_enum(JlptLevel))
    goal: Mapped[UserGoal | None] = mapped_column(str_enum(UserGoal))
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Lifecycle: set when the user asks to delete the account; anonymized after DELETION_GRACE_DAYS
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
