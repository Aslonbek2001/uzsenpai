"""API contract for email + password sign-up, sign-in and password reset."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from app.modules.auth.domain.rules import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, VERIFICATION_CODE_DIGITS

Password = Annotated[str, StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)]
Code = Annotated[str, StringConstraints(pattern=rf"^\d{{{VERIFICATION_CODE_DIGITS}}}$")]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterIn(_Strict):
    """Step 1: just the email — a code is sent to it."""

    email: EmailStr


class VerifyEmailIn(_Strict):
    """Step 2: the code plus the account details. Only the mailbox owner has the code, so only they set the
    password (a password sent in step 1 could be replaced by an attacker's request)."""

    email: EmailStr
    code: Code
    password: Password
    display_name: DisplayName


class LoginIn(_Strict):
    email: EmailStr
    password: Annotated[str, StringConstraints(max_length=PASSWORD_MAX_LENGTH)]


class ForgotPasswordIn(_Strict):
    email: EmailStr


class ResetPasswordIn(_Strict):
    email: EmailStr
    code: Code
    new_password: Password
