"""Traduccion de errores de dominio a respuestas HTTP."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fastapi_2026.core.exceptions import DomainError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )
