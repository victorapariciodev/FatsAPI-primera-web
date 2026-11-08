from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi_2026.core.templates import templates
from fastapi_2026.services.auth import AuthService
from fastapi_2026.api.deps import _set_session_cookies, _is_https, _clear_session_cookies

router = APIRouter()
auth_service = AuthService() # Instanciamos el servicio

# ================= LOGIN =================
@router.get("/login")
async def login_page(request: Request):
    # ¡OJO! Como tu html está en templates/auth/, debes poner "auth/login.html"
    return templates.TemplateResponse(request=request, name="auth/login.html")

@router.post("/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        # 1. Llamamos al servicio
        session = await auth_service.sign_in(email, password)
        
        # 2. Redirigimos al menú
        redirect = RedirectResponse(url="/menu", status_code=303)
        
        # 3. Seteamos las cookies
        _set_session_cookies(
            response=redirect, 
            access=session.access_token, 
            refresh=session.refresh_token, 
            secure=_is_https(request)
        )
        return redirect
    except Exception:
        return templates.TemplateResponse(
            request=request, 
            name="auth/login.html", 
            context={"error": "Correo o contraseña incorrectos"}
        )

# ================= REGISTER =================
@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth/register.html")

@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    national_id: str = Form(...),
    phone_number: str = Form(...),
    gender: str = Form(...)
):
    try:
        # 1. Agrupamos los datos personales en un diccionario (metadata)
        profile_data = {
            "first_name": first_name,
            "last_name": last_name,
            "national_id": national_id,
            "phone_number": phone_number,
            "gender": gender
        }

        # 2. Llamamos al servicio pasando email, password y los datos
        session = await auth_service.sign_up(email, password, profile_data)
        
        if session:
            # Logueo automático
            redirect = RedirectResponse(url="/menu", status_code=303)
            _set_session_cookies(
                response=redirect, 
                access=session.access_token, 
                refresh=session.refresh_token, 
                secure=_is_https(request)
            )
            return redirect
        else:
            return templates.TemplateResponse(
                request=request, 
                name="auth/login.html", 
                context={"mensaje": "Registro exitoso. Revisa tu correo para confirmar."}
            )
    except Exception as e:
        print(f"Error en registro: {e}") # Para ver el error real en consola
        return templates.TemplateResponse(
            request=request, 
            name="auth/register.html", 
            context={"error": "Error en el registro. La cédula o correo ya existen."}
        )
# ================= LOGOUT =================
@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    _clear_session_cookies(response)
    return response