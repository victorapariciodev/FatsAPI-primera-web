import jwt
from jwt import PyJWKClient
from fastapi_2026.core.config import settings
from fastapi import HTTPException

# Construimos la URL de JWKS automáticamente si no está en el .env
jwks_url = settings.supabase_jwks_url or f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"

_jwks_client = PyJWKClient(jwks_url, cache_keys=True)


def verify_supabase_jwt(token: str) -> dict:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            options={"verify_aud": False, "verify_exp": True} # Desactivamos aud por ahora
        )
        return data
    except Exception as e:
        print(f" JWT VALIDATOR ERROR: {e}") # <--- AÑADE ESTO
        raise HTTPException(status_code=401, detail=str(e))