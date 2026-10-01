"""/api/v1/auth/email/* — sign-up with a code, sign-in, password reset."""

from fastapi import APIRouter, Response, status

from app.modules.auth.routers.cookies import tokens_response
from app.modules.auth.routers.deps import Client, EmailAuth, RequestLocale
from app.modules.auth.schemas import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, TokenOut, VerifyEmailIn

router = APIRouter(prefix="/email")


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register(data: RegisterIn, auth: EmailAuth, locale: RequestLocale, client: Client) -> None:
    """Emails a 6-digit code. Always 202 — the answer never reveals whether the email is registered."""
    await auth.register(data, locale, client)


@router.post("/verify", response_model=TokenOut)
async def verify(data: VerifyEmailIn, auth: EmailAuth, client: Client, response: Response) -> TokenOut:
    """Creates the account from the code and signs in."""
    return tokens_response(response, await auth.verify_email(data, client))


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, auth: EmailAuth, client: Client, response: Response) -> TokenOut:
    return tokens_response(response, await auth.login(data, client))


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(data: ForgotPasswordIn, auth: EmailAuth, locale: RequestLocale, client: Client) -> None:
    await auth.forgot_password(data, locale, client)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: ResetPasswordIn, auth: EmailAuth, client: Client) -> None:
    """Sets the new password and signs out every device; the user then signs in again."""
    await auth.reset_password(data, client)
