"""Cliente de base de datos para la tienda.

Se usa el cliente con SERVICE_ROLE_KEY porque el backend hace escrituras
(stock, ordenes) que el cliente anonimo no puede hacer. Consecuencia directa:
RLS NO nos protege en estas queries, por eso cada consulta de carrito/orden
filtra explicitamente por el user_id del JWT.
"""

from functools import lru_cache

from fastapi import HTTPException, status
from supabase import Client

from fastapi_2026.services.auth import AuthService


@lru_cache(maxsize=1)
def _admin_client() -> Client:
    auth_service = AuthService()
    if auth_service.admin_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Falta SUPABASE_SERVICE_ROLE_KEY en el .env: sin esa llave "
                "el backend no puede gestionar stock ni ordenes."
            ),
        )
    return auth_service.admin_client


def get_db() -> Client:
    """Dependencia de FastAPI: inyecta el cliente de base de datos."""
    return _admin_client()
