from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class ProviderScope(StrEnum):
    NATIONAL = "national"  # Uzbekistan: Click, Payme, Uzum (UZS, local cards Uzcard/Humo)
    INTERNATIONAL = "international"  # Visa/Mastercard/JCB… in USD/JPY/EUR — provider chosen by ADR
