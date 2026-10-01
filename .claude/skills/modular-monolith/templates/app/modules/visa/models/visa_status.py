import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VisaStatus(Base):
    __tablename__ = "visa_statuses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Another module's id: stored, NOT a foreign key (resolve through users.public if needed)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    residence_status: Mapped[str] = mapped_column(String(50))
    expires_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
