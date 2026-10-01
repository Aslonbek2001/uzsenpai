"""Payme Merchant API error codes used by the adapter. VERIFY against the current official docs."""

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
AUTH_FAILED = -32504
WRONG_AMOUNT = -31001
TRANSACTION_NOT_FOUND = -31003
CANNOT_CANCEL = -31007
CANNOT_PERFORM = -31008
ORDER_NOT_FOUND = -31050  # -31050..-31099: account (order) errors
ORDER_BUSY = -31051  # another Payme transaction already exists for this order


def rpc_error(request_id: object, code: int, message: str) -> dict[str, object]:
    return {"id": request_id, "error": {"code": code, "message": {"en": message, "ru": message, "uz": message}}}
