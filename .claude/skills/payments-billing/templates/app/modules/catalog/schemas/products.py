"""Public product cards: localized text + the price in the requested checkout currency."""

from pydantic import BaseModel


class PriceOut(BaseModel):
    amount_minor: int
    currency: str


class ProductOut(BaseModel):
    id: str
    title: str
    includes: list[str]
    lang: str  # language actually returned (falls back to uz)
    fulfilment: str
    price: PriceOut
