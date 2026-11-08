# src/fastapi_2026/api/routes/profile.py
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi_2026.api.deps import get_current_user
from fastapi_2026.services.auth import AuthService
from fastapi_2026.services.profile import ProfileService

router = APIRouter()

def get_db():
    auth_service = AuthService()
    # Verificamos estrictamente que el admin_client exista
    if not auth_service.admin_client:
        print("🚨 ERROR: No se encontró admin_client. Revisa SUPABASE_SERVICE_ROLE_KEY en tu .env")
        raise HTTPException(
            status_code=500, 
            detail="Error de configuración en el servidor. Falta la llave de administrador (Service Role)."
        )
    return auth_service.admin_client

@router.post("/profile/employment")
async def save_employment(
    request: Request,
    user_token: dict = Depends(get_current_user),
    company_name: str = Form(...),
    job_title: str = Form(...),
    salary: float = Form(...),
    company_address: str = Form(...)
):
    db = get_db()
    profile_service = ProfileService(db)
    
    data = {
        "company_name": company_name,
        "job_title": job_title,
        "salary": salary,
        "company_address": company_address
    }
    
    try:
        profile_service.save_employment(user_token['sub'], data)
    except Exception as e:
        print(f"🚨 Error al guardar empleo en BD: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar los datos laborales.")
        
    return RedirectResponse(url="/menu", status_code=303)


@router.post("/profile/education")
async def save_education(
    request: Request,
    user_token: dict = Depends(get_current_user),
    academic_degree: str = Form(...),
    field_of_study: str = Form(...),
    tcu_status: str = Form(...)
):
    db = get_db()
    profile_service = ProfileService(db)
    
    data = {
        "academic_degree": academic_degree,
        "field_of_study": field_of_study,
        "tcu_status": tcu_status
    }
    
    try:
        profile_service.save_education(user_token['sub'], data)
    except Exception as e:
        print(f"🚨 Error al guardar estudios en BD: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar los datos académicos.")

    return RedirectResponse(url="/menu", status_code=303)


@router.post("/profile/banking")
async def save_banking(
    request: Request,
    user_token: dict = Depends(get_current_user),
    bank_name: str = Form(...),
    account_type: str = Form(...),
    account_number: str = Form(...)
):
    db = get_db()
    profile_service = ProfileService(db)
    
    data = {
        "bank_name": bank_name,
        "account_type": account_type,
        "account_number": account_number
    }
    
    try:
        profile_service.save_banking(user_token['sub'], data)
    except Exception as e:
        print(f"🚨 Error al guardar banco en BD: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar los datos bancarios.")

    return RedirectResponse(url="/menu", status_code=303)