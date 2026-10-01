"""argon2id password hashing, run in a thread so ~50 ms of CPU per hash never blocks the event loop."""

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # argon2id with the library's current recommended parameters
# Verified when the email is unknown, so "no such account" costs the same time as "wrong password".
_DUMMY_HASH = _hasher.hash("timing-equalizer")


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(password_hash: str | None, password: str) -> tuple[bool, bool]:
    """(matches, needs_rehash). A missing hash still burns one verification."""
    try:
        await asyncio.to_thread(_hasher.verify, password_hash or _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False, False
    if password_hash is None:
        return False, False
    return True, _hasher.check_needs_rehash(password_hash)
