from supabase import create_client, Client
from fastapi_2026.core.config import settings
from fastapi import HTTPException

class AuthService:
    def __init__(self):
        # Cliente público (para login/registro de usuarios)
        self.anon_client: Client = create_client(
            settings.supabase_url, 
            settings.supabase_publishable_key  # Usamos la nueva variable
        )
        
        # Cliente admin (opcional, solo si tienes la llave en el .env)
        self.admin_client = None
        if settings.supabase_service_role_key:
            self.admin_client = create_client(
                settings.supabase_url, 
                settings.supabase_service_role_key
            )

    async def sign_in(self, email: str, password: str):
        try:
            response = self.anon_client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            return response.session
        except Exception as e:
            print(f"ERROR SUPABASE: {e}") # <--- AÑADE ESTO
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

    async def sign_up(self, email: str, password: str, profile_data: dict):
        try:
            # ENVIAMOS LOS DATOS EN 'options' -> 'data'
            response = self.anon_client.auth.sign_up({
                "email": email, 
                "password": password,
                "options": {
                    "data": profile_data # <-- AQUÍ VAN LOS DATOS PARA EL TRIGGER
                }
            })
            return response.session
        except Exception as e:
            print(f"Error en Supabase sign_up: {e}")
            raise HTTPException(status_code=400, detail="Error en el registro")

    async def refresh_session(self, refresh_token: str):
        try:
            response = self.anon_client.auth.refresh_session(refresh_token)
            return response.session
        except Exception:
            raise HTTPException(status_code=401, detail="Sesión expirada")