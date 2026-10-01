import uuid
from dataclasses import dataclass

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PaymentSucceeded(DomainEvent):
    payment_id: uuid.UUID
    user_id: uuid.UUID
    product_id: str
    fulfilment: str  # ai | human → orders creates an order for "human"
