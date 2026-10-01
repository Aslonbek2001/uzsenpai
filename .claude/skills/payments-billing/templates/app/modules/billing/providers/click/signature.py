"""Click SHOP-API request signature (MD5). VERIFY the field order against the current official docs."""

import hashlib
import hmac


def expected_sign(
    *,
    click_trans_id: str,
    service_id: str,
    secret_key: str,
    merchant_trans_id: str,
    amount: str,
    action: str,
    sign_time: str,
    merchant_prepare_id: str | None = None,
) -> str:
    parts = [click_trans_id, service_id, secret_key, merchant_trans_id]
    if merchant_prepare_id is not None:  # only on "complete" (action=1)
        parts.append(merchant_prepare_id)
    parts += [amount, action, sign_time]
    return hashlib.md5("".join(parts).encode()).hexdigest()  # noqa: S324 — mandated by the provider


def is_valid(received: str, **fields: str | None) -> bool:
    return hmac.compare_digest(received, expected_sign(**fields))  # type: ignore[arg-type]
