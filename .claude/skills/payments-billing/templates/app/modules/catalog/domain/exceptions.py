from app.shared.errors import AppError, NotFound


class ProductNotFound(NotFound):
    pass


class PriceNotAvailable(AppError):
    """Product is not sold in the requested currency."""

    status = 422
