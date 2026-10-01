import uuid

from pydantic import BaseModel, Field


class CheckoutIn(BaseModel):
    product_id: str = Field(max_length=64)
    currency: str = Field(pattern="^[A-Z]{3}$", description="UZS → national providers, others → international")
    provider: str | None = Field(default=None, description="Optional; must be offered for the currency")


class CheckoutOut(BaseModel):
    payment_id: uuid.UUID
    provider: str
    redirect_url: str
