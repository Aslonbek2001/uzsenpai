"""Payme JSON-RPC params (validated before use)."""

from pydantic import UUID4, BaseModel, StrictInt


class Account(BaseModel):
    payment_id: UUID4


class CheckPerformParams(BaseModel):
    amount: StrictInt
    account: Account


class CreateParams(BaseModel):
    id: str
    time: StrictInt
    amount: StrictInt
    account: Account


class TxnParams(BaseModel):
    id: str


class CancelParams(BaseModel):
    id: str
    reason: StrictInt | None = None
