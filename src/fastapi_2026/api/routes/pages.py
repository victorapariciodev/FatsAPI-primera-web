# src/fastapi_2026/api/routes/pages.py
"""Paginas heredadas del proyecto base: inicio y el menu de perfil.

El menu de perfil ya no es la puerta de entrada (ver ``services.onboarding``):
el login va a ``/bienvenida``, que decide entre este formulario y la tienda.
Aqui queda accesible para editar los datos cuando el usuario quiera, y sigue
cayendo a los datos del JWT si la base no responde.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import get_optional_user
from fastapi_2026.core.templates import templates
from fastapi_2026.services.onboarding import debe_hacer_onboarding, marcar_visto

router = APIRouter()

# Para un anonimo estas paginas son un redirect, no un 401 en JSON.
IR_AL_LOGIN = RedirectResponse(url="/login", status_code=303)

# Tabla -> nombre del bloque en el contexto de la plantilla.
BLOQUES = {
    "employment_details": "employment",
    "education_records": "education",
    "banking_info": "banking",
}


def _una_fila(db: Client, tabla: str, user_id: str) -> dict | None:
    filas = db.table(tabla).select("*").eq("profile_id", user_id).execute().data
    return filas[0] if filas else None


def _contexto_perfil(db: Client, user_id: str, claims: dict) -> dict:
    """Arma el contexto de menu.html.

    Si la base falla se usa lo que trae el JWT: la pagina es informativa y no
    debe reventar por un error de configuracion. El email vive en el claim de
    nivel superior, no en user_metadata, asi que se inyecta aparte.
    """
    metadatos = {"email": claims.get("email"), **(claims.get("user_metadata") or {})}

    try:
        perfil = db.table("profiles").select("*").eq("id", user_id).execute().data
        perfil = perfil[0] if perfil else metadatos

        contexto = {"user": perfil}
        for tabla, bloque in BLOQUES.items():
            contexto[bloque] = _una_fila(db, tabla, user_id)

        bonuses = (
            db.table("bonus_payments").select("*").eq("profile_id", user_id).execute().data
        )
        contexto["bonuses"] = bonuses or []
        return contexto
    except Exception as exc:  # noqa: BLE001 - se degrada a los datos del JWT
        print(f"🚨 No se pudo leer el perfil, se usa el JWT: {exc}")
        return {
            "user": metadatos,
            "employment": None,
            "education": None,
            "banking": None,
            "bonuses": [],
        }


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"titulo": "Inicio"},
    )


@router.get("/menu")
async def menu(
    request: Request,
    user_token: dict | None = Depends(get_optional_user),
    db: Client = Depends(get_db),
):
    """Edicion del perfil. Ya no es la puerta de entrada del login."""
    if user_token is None:
        return IR_AL_LOGIN
    return templates.TemplateResponse(
        request=request,
        name="menu.html",
        context=_contexto_perfil(db, user_token["sub"], user_token),
    )


@router.get("/bienvenida")
async def bienvenida(
    request: Request,
    user_token: dict | None = Depends(get_optional_user),
    db: Client = Depends(get_db),
):
    """Paso de perfil de primer ingreso.

    Si ya se cumplio (o si la base no responde) se sigue a la tienda: esto es
    un tramite de una sola vez, no un peaje.
    """
    if user_token is None:
        return IR_AL_LOGIN

    if not debe_hacer_onboarding(db, user_token["sub"]):
        return RedirectResponse(url="/tienda", status_code=303)

    contexto = _contexto_perfil(db, user_token["sub"], user_token)
    contexto["primer_ingreso"] = True
    return templates.TemplateResponse(request=request, name="menu.html", context=contexto)


@router.post("/bienvenida/saltar")
async def saltar_bienvenida(
    user_token: dict | None = Depends(get_optional_user),
    db: Client = Depends(get_db),
):
    """Cierra el paso sin llenar nada y manda a la tienda."""
    if user_token is None:
        return IR_AL_LOGIN

    try:
        marcar_visto(db, user_token["sub"])
    except Exception as exc:  # noqa: BLE001 - no se bloquea al usuario por esto
        print(f"🚨 No se pudo marcar el paso como visto: {exc}")
    return RedirectResponse(url="/tienda", status_code=303)


@router.get("/debug-menu")
async def debug_menu(
    user_token: dict | None = Depends(get_optional_user),
    db: Client = Depends(get_db),
):
    if user_token is None:
        return IR_AL_LOGIN
    perfil = db.table("profiles").select("*").eq("id", user_token["sub"]).execute()
    return {
        "jwt_payload": user_token,
        "supabase_data": perfil.data,
    }
