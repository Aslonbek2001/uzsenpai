from app.shared.errors import AppError, Forbidden, NotFound


class InvalidTransition(AppError):
    status = 409


class AmountMismatch(AppError):
    status = 409


class AlreadyPaid(AppError):
    """Paid already by another provider transaction — never grant twice."""

    status = 409


class TxnAlreadyUsed(AppError):
    """This provider transaction id already belongs to another payment."""

    status = 409


class PaymentNotFound(NotFound):
    pass


class ProviderNotAvailable(AppError):
    status = 422


class NoEntitlement(Forbidden):
    pass


class InvalidSignature(AppError):
    status = 401


class InvalidPayload(AppError):
    status = 400
