"""Diagnostico de la conexion con Supabase.

Nace de un dolor concreto: con la API key equivocada, cada pagina devolvia un
500 identico y sin pistas. Un error de configuracion no puede disfrazarse de
bug de la aplicacion, asi que aqui se clasifica la causa y se dice que hacer.

No expone secretos: solo nombres de tabla y el motivo del fallo.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

# Orden de dependencia: primero el catalogo, al final las ordenes.
TABLAS = (
    "products",
    "product_variants",
    "carts",
    "cart_items",
    "orders",
    "order_items",
)

FALTA_ESQUEMA = "Falta ejecutar db/store_schema.sql en el SQL Editor de Supabase."
LLAVE_INVALIDA = (
    "La API key no esta registrada en este proyecto. Copia de nuevo "
    "SUPABASE_PUBLISHABLE_KEY y SUPABASE_SERVICE_ROLE_KEY desde "
    "Project Settings > API Keys."
)
LLAVE_EQUIVOCADA = (
    "Estas usando la publishable key donde hace falta la secret key "
    "(SUPABASE_SERVICE_ROLE_KEY)."
)


def _texto_completo(exc: Exception) -> str:
    """Junta todo lo que trae el error.

    PostgREST a veces devuelve el motivo real dentro de ``details`` (bytes) y
    deja un ``message`` inutil como "JSON could not be generated". Si solo se
    mira ``.message`` se pierde la causa, que es justo lo que hay que reportar.
    """
    detalles = getattr(exc, "details", None)
    if isinstance(detalles, (bytes, bytearray)):
        detalles = detalles.decode("utf-8", "replace")

    partes = (
        str(exc),
        str(getattr(exc, "code", "") or ""),
        str(getattr(exc, "message", "") or ""),
        str(getattr(exc, "hint", "") or ""),
        str(detalles or ""),
    )
    return " ".join(partes).lower()


def clasificar_error(exc: Exception) -> str:
    """Traduce el error crudo a una instruccion accionable."""
    texto = _texto_completo(exc)

    if "unregistered api key" in texto or "invalid api key" in texto:
        return LLAVE_INVALIDA
    if "secret api key required" in texto:
        return LLAVE_EQUIVOCADA
    if "could not find the table" in texto or "pgrst205" in texto:
        return FALTA_ESQUEMA
    if "permission denied" in texto:
        return (
            "La llave no tiene permisos sobre las tablas. Revisa que sea la "
            "service_role y no una llave restringida."
        )
    if "getaddrinfo" in texto or "connection" in texto:
        return "No se pudo alcanzar el proyecto: revisa SUPABASE_URL y tu red."

    crudo = getattr(exc, "message", None) or str(exc)
    return f"{type(exc).__name__}: {crudo[:300]}"


def check_database(db: Client) -> dict[str, Any]:
    """Verifica, tabla por tabla, que el esquema responde."""
    checks: list[dict[str, Any]] = []

    for tabla in TABLAS:
        try:
            db.table(tabla).select("id").limit(1).execute()
            checks.append({"tabla": tabla, "ok": True})
        except Exception as exc:  # noqa: BLE001 - se reporta, no se propaga
            checks.append(
                {"tabla": tabla, "ok": False, "detalle": clasificar_error(exc)}
            )

    fallos = [check for check in checks if not check["ok"]]

    return {
        "ok": not fallos,
        "tablas_ok": len(checks) - len(fallos),
        "tablas_total": len(checks),
        "checks": checks,
        "sugerencia": fallos[0]["detalle"] if fallos else None,
    }
