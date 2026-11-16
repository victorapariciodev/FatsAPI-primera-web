"""Excepciones de dominio de la tienda.

La capa de servicios NO conoce HTTP: lanza estos errores y la capa de
transporte (api/) los traduce a codigos de estado. Asi la logica de negocio
se puede probar sin levantar FastAPI.
"""

from __future__ import annotations


class DomainError(Exception):
    """Error de negocio con su equivalente HTTP."""

    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class StockError(ConflictError):
    """No hay unidades suficientes para completar la operacion."""

    code = "insufficient_stock"


class InvalidOperation(ConflictError):
    """La operacion no es valida en el estado actual del recurso."""

    code = "invalid_operation"
