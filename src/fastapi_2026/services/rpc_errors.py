"""Traduccion de errores de las funciones RPC de Postgres a errores de dominio.

Las RPC levantan ``raise exception 'CODIGO'``. PostgREST lo devuelve como error
SQL (P0001). Parsear el mensaje es fragil por naturaleza, por eso los codigos
son constantes en MAYUSCULAS y sin acentos: cualquier cambio en el SQL debe
mantener el contrato.
"""

from __future__ import annotations

from fastapi_2026.core.exceptions import (
    DomainError,
    InvalidOperation,
    NotFoundError,
    StockError,
)

_RAW_TO_DOMAIN = {
    "CARRITO_VACIO": lambda: InvalidOperation("El carrito esta vacio."),
    "CANTIDAD_INVALIDA": lambda: DomainError("La cantidad debe ser mayor que cero."),
    "VARIANTE_NO_EXISTE": lambda: NotFoundError("La variante solicitada no existe."),
    "PRODUCTO_NO_DISPONIBLE": lambda: InvalidOperation("El producto ya no esta disponible."),
    "ORDEN_NO_EXISTE": lambda: NotFoundError("La orden no existe o no te pertenece."),
    "ORDEN_NO_CANCELABLE": lambda: InvalidOperation(
        "Solo se pueden cancelar ordenes en estado 'pending'."
    ),
}


def _tail(raw: str, marker: str) -> str | None:
    """Texto que sigue al codigo de error.

    Tolerante a los dos formatos que se ven en la practica:
      'STOCK_INSUFICIENTE:Camisa'            (mensaje crudo de PostgREST)
      'P0001: STOCK_INSUFICIENTE: Camisa'    (str() de la excepcion)
    Cortar por el primer ':' devolvia ' STOCK_INSUFICIENTE: Camisa' en el
    segundo caso, y ese texto terminaba mostrandose en la UI.
    """
    if marker not in raw:
        return None
    resto = raw.split(marker, 1)[1].lstrip(": ").strip()
    return resto or None


def rpc_error(exc: Exception) -> DomainError:
    """Convierte una excepcion de supabase-py en un DomainError."""
    raw = getattr(exc, "message", None) or str(exc)

    if "STOCK_INSUFICIENTE" in raw:
        detail = _tail(raw, "STOCK_INSUFICIENTE")
        suffix = f" Producto: {detail}." if detail else ""
        return StockError(f"No hay stock suficiente para completar la compra.{suffix}")

    if "PRODUCTO_NO_DISPONIBLE" in raw:
        name = _tail(raw, "PRODUCTO_NO_DISPONIBLE") or "desconocido"
        return InvalidOperation(f"El producto '{name}' ya no esta disponible.")

    for code, factory in _RAW_TO_DOMAIN.items():
        if code in raw:
            return factory()

    return DomainError("Ocurrio un error inesperado al operar con la base de datos.")
