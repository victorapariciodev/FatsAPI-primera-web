# src/fastapi_2026/api/routes/profile.py
"""Guardado del menu de perfil (empleo, estudios, banco).

El cliente de base viene de ``api.db.get_db``: una sola puerta para el
cliente admin (y asi los tests pueden inyectar su doble sin tocar la red).

Al terminar cada seccion se vuelve a ``/bienvenida``, que es quien decide:
si ya estan las tres, cierra el paso y manda a la tienda.
"""

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import get_current_user
from fastapi_2026.services.onboarding import marcar_visto, perfil_completo
from fastapi_2026.services.profile import ProfileService

router = APIRouter()


def _siguiente_paso(db: Client, user_id: str) -> RedirectResponse:
    """Cierra el paso si el perfil quedo completo; siempre vuelve a decidir."""
    try:
        if perfil_completo(db, user_id):
            marcar_visto(db, user_id)
    except Exception as exc:  # noqa: BLE001 - guardar ya funciono; esto es extra
        print(f"🚨 No se pudo evaluar si el perfil quedo completo: {exc}")
    return RedirectResponse(url="/bienvenida", status_code=303)


@router.post("/profile/employment")
async def save_employment(
    user_token: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
    company_name: str = Form(...),
    job_title: str = Form(...),
    salary: float = Form(...),
    company_address: str = Form(...),
):
    data = {
        "company_name": company_name,
        "job_title": job_title,
        "salary": salary,
        "company_address": company_address,
    }

    try:
        ProfileService(db).save_employment(user_token["sub"], data)
    except Exception as exc:
        print(f"🚨 Error al guardar empleo en BD: {exc}")
        raise HTTPException(status_code=500, detail="Error al guardar los datos laborales.")

    return _siguiente_paso(db, user_token["sub"])


@router.post("/profile/education")
async def save_education(
    user_token: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
    academic_degree: str = Form(...),
    field_of_study: str = Form(...),
    tcu_status: str = Form(...),
):
    data = {
        "academic_degree": academic_degree,
        "field_of_study": field_of_study,
        "tcu_status": tcu_status,
    }

    try:
        ProfileService(db).save_education(user_token["sub"], data)
    except Exception as exc:
        print(f"🚨 Error al guardar estudios en BD: {exc}")
        raise HTTPException(status_code=500, detail="Error al guardar los datos académicos.")

    return _siguiente_paso(db, user_token["sub"])


@router.post("/profile/banking")
async def save_banking(
    user_token: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
    bank_name: str = Form(...),
    account_type: str = Form(...),
    account_number: str = Form(...),
):
    data = {
        "bank_name": bank_name,
        "account_type": account_type,
        "account_number": account_number,
    }

    try:
        ProfileService(db).save_banking(user_token["sub"], data)
    except Exception as exc:
        print(f"🚨 Error al guardar banco en BD: {exc}")
        raise HTTPException(status_code=500, detail="Error al guardar los datos bancarios.")

    return _siguiente_paso(db, user_token["sub"])
