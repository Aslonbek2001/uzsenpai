"""app/shared/errors.py — errors carry a stable code; clients translate it (uz/ru/en/ja)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """code: '<module>.<snake_reason>' e.g. 'visa.expiry_in_past'. Never a human sentence."""

    status: int = 400

    def __init__(self, code: str, *, status: int | None = None, params: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.params = params or {}
        if status is not None:
            self.status = status


class NotFound(AppError):
    status = 404


class Forbidden(AppError):
    status = 403


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "params": exc.params}})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 401/404/405 from FastAPI itself still reach clients as translatable codes
        code = {
            401: "common.unauthorized",
            403: "common.forbidden",
            404: "common.not_found",
            405: "common.method_not_allowed",
            429: "common.rate_limited",
        }.get(exc.status_code, "common.http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "params": {}}},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        return JSONResponse(
            status_code=422, content={"error": {"code": "common.validation", "params": {"fields": fields}}}
        )
