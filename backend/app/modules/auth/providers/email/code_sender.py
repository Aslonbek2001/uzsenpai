"""Delivery of verification / reset codes by email.

The real sender (Resend, localized templates in uz/ru/en/ja) arrives with the `notifications` module. Until
then only `LogCodeSender` exists, and it is refused outside local/test (see routers/deps.get_code_sender).
"""

import logging
from typing import Protocol

from app.modules.auth.domain.enums import CodePurpose
from app.shared.i18n import Locale

log = logging.getLogger(__name__)


class CodeSender(Protocol):
    async def send(self, *, email: str, code: str, purpose: CodePurpose, locale: Locale) -> None: ...


class LogCodeSender:
    """Local development: prints the code to the API log instead of emailing it."""

    async def send(self, *, email: str, code: str, purpose: CodePurpose, locale: Locale) -> None:
        log.info("auth code (local only) purpose=%s email=%s locale=%s code=%s", purpose, email, locale, code)
