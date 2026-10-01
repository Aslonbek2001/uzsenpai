from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Product(Base):
    __tablename__ = "catalog_products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # slug, e.g. "resume-expert-review"
    title: Mapped[dict[str, str]] = mapped_column(JSON)  # LocalizedText {uz, ru, en, ja}
    includes: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)  # list of LocalizedText bullets
    # What a purchase grants: [{"key": "interview.mock_session", "quantity": 3, "days": null}, ...]
    grants: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    fulfilment: Mapped[str] = mapped_column(String(10), default="ai")  # ai | human
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProductPrice(Base):
    """One row per currency — no FX conversion: UZS for national, USD/JPY/EUR for international checkout."""

    __tablename__ = "catalog_product_prices"
    __table_args__ = (UniqueConstraint("product_id", "currency"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Same module → a real foreign key is fine
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
