"""Telegram Login Widget data check — https://core.telegram.org/widgets/login#checking-authorization

data_check_string = "\\n".join(sorted("key=value" for every field except hash))
secret_key        = SHA256(bot_token)
valid            ⇔ hex(HMAC_SHA256(secret_key, data_check_string)) == hash  and  auth_date is recent
"""

import hashlib
import hmac
from collections.abc import Mapping
from datetime import timedelta


def verify_login_widget(fields: Mapping[str, str], *, bot_token: str, now: int, max_age: timedelta) -> bool:
    received_hash = fields.get("hash", "")
    auth_date = fields.get("auth_date", "")
    if not bot_token or not received_hash or not auth_date.isdigit():
        return False
    if now - int(auth_date) > max_age.total_seconds():
        return False
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()) if key != "hash")
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_hash)
