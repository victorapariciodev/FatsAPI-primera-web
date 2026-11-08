# src/fastapi_2026/api/routes/pages.py
from fastapi import APIRouter, Request, Depends
from fastapi_2026.core.templates import templates
from fastapi_2026.api.deps import get_current_user
from fastapi_2026.services.auth import AuthService

router = APIRouter()

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"titulo": "Inicio"}
    )

@router.get("/menu")
async def menu(request: Request, user_token: dict = Depends(get_current_user)):
    user_id = user_token['sub'] 
    
    auth_service = AuthService()
    db = auth_service.admin_client if auth_service.admin_client else auth_service.anon_client

    try:
        # Intentamos leer de la base de datos
        profile_res = db.table('profiles').select('*').eq('id', user_id).execute()
        
        # ¡LA MAGIA! Si la base de datos devuelve vacío, usamos los datos del JWT
        if not profile_res.data:
            profile = user_token.get('user_metadata', {})
        else:
            profile = profile_res.data[0]

        # Consultamos las otras tablas (estas sí deberían estar vacías por ahora)
        emp_res = db.table('employment_details').select('*').eq('profile_id', user_id).execute()
        employment = emp_res.data[0] if emp_res.data else None

        edu_res = db.table('education_records').select('*').eq('profile_id', user_id).execute()
        education = edu_res.data[0] if edu_res.data else None

        bank_res = db.table('banking_info').select('*').eq('profile_id', user_id).execute()
        banking = bank_res.data[0] if bank_res.data else None

        bonus_res = db.table('bonus_payments').select('*').eq('profile_id', user_id).execute()
        bonuses = bonus_res.data if bonus_res.data else []

    except Exception as e:
        print(f"🚨 DEBUG: ERROR: {e}")
        profile = user_token.get('user_metadata', {})
        employment = education = banking = None
        bonuses = []

    return templates.TemplateResponse(
        request=request,
        name="menu.html",
        context={
            "user": profile, 
            "employment": employment,
            "education": education,
            "banking": banking,
            "bonuses": bonuses
        }
    )

@router.get("/debug-menu")
async def debug_menu(user_token: dict = Depends(get_current_user)):
    user_id = user_token['sub'] 
    
    auth_service = AuthService()
    db = auth_service.admin_client if auth_service.admin_client else auth_service.anon_client
    
    # Consultamos el perfil
    profile_res = db.table('profiles').select('*').eq('id', user_id).execute()
    
    # Devolvemos un JSON puro para ver qué está pasando realmente
    return {
        "jwt_payload": user_token,
        "supabase_data": profile_res.data,
        "usando_admin_client": bool(auth_service.admin_client)
    }