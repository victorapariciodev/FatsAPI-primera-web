"""Endpoints de salud: sirven para verificar configuracion, no para la tienda.

``GET /health/db`` responde 200 incluso cuando algo falla, y el cuerpo dice si
la base esta usable y por que no. Se separa a proposito de ``/api/*``: no es
un recurso de negocio ni requiere sesion.
"""

from typing import Any

from fastapi import APIRouter, Depends
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.services.health import check_database

router = APIRouter(prefix="/health", tags=["Salud"])


@router.get("", summary="Estado del servidor")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db", summary="Diagnostico de la conexion con Supabase")
def health_db(db: Client = Depends(get_db)) -> dict[str, Any]:
    return check_database(db)
