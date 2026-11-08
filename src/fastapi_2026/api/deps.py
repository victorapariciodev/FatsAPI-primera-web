from fastapi import Request, Response, HTTPException, status
from typing import Optional
from fastapi_2026.services.jwt_validator import verify_supabase_jwt
from fastapi_2026.services.auth import AuthService

ACCESS_COOKIE = "sb_access"
REFRESH_COOKIE = "sb_refresh"

def _set_session_cookies(response: Response, access: str, refresh: str, secure: bool):
    common = dict(httponly=True, samesite="lax", secure=secure, path="/")
    response.set_cookie(ACCESS_COOKIE, access, max_age=3600, **common)
    response.set_cookie(REFRESH_COOKIE, refresh, max_age=2592000, **common) 

def _clear_session_cookies(response: Response):
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")

def _is_https(request: Request) -> bool:
    return (
        request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"
        or request.url.scheme == "https"
    )

# async def get_current_user(request: Request, response: Response) -> dict:
# access = request.cookies.get(ACCESS_COOKIE)
# refresh = request.cookies.get(REFRESH_COOKIE)

# if not access and not refresh:
#     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

# if access:
#     try:
#         payload = verify_supabase_jwt(access)
#         return payload
#     except HTTPException:
#         pass 

# if refresh:
#     auth_service = AuthService()
#     try:
#         session = await auth_service.refresh_session(refresh)
#         _set_session_cookies(response, session.access_token, session.refresh_token, _is_https(request))
#         payload = verify_supabase_jwt(session.access_token)
#         return payload
#     except HTTPException:
#         _clear_session_cookies(response)
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

# _clear_session_cookies(response)
# raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

async def get_current_user(request: Request, response: Response) -> dict:
    access = request.cookies.get(ACCESS_COOKIE)
    refresh = request.cookies.get(REFRESH_COOKIE)

    print(f"\n🛡️ GUARDIÁN: access={'SI' if access else 'NO'}, refresh={'SI' if refresh else 'NO'}")

    if not access and not refresh:
        print("❌ GUARDIÁN: No hay cookies en absoluto.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if access:
        try:
            payload = verify_supabase_jwt(access)
            print("✅ GUARDIÁN: Token verificado con éxito.")
            return payload
        except HTTPException as e:
            print(f"⚠️ GUARDIÁN: Falló validación local, intentando refresh. Motivo: {e.detail}")
            pass 

    if refresh:
        auth_service = AuthService()
        try:
            print("🔄 GUARDIÁN: Intentando refrescar sesión...")
            session = await auth_service.refresh_session(refresh)
            _set_session_cookies(response, session.access_token, session.refresh_token, _is_https(request))
            payload = verify_supabase_jwt(session.access_token)
            print("✅ GUARDIÁN: Refresh exitoso.")
            return payload
        except HTTPException as e:
            print(f"❌ GUARDIÁN: Falló el refresh. Motivo: {e.detail}")
            _clear_session_cookies(response)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    _clear_session_cookies(response)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")