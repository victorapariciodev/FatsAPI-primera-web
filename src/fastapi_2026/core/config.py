from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from dotenv import load_dotenv

# Subimos solo 1 nivel: de 'core' a 'fastapi_2026'
BASE_DIR = Path(__file__).resolve().parent.parent 
ENV_FILE_PATH = BASE_DIR / ".env"

# Forzamos la carga
if ENV_FILE_PATH.exists():
    print(f"✅ Archivo .env encontrado en: {ENV_FILE_PATH}")
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
else:
    print(f"❌ ERROR: No se encontró el archivo .env en: {ENV_FILE_PATH}")

class Settings(BaseSettings):
    supabase_url: str
    supabase_publishable_key: str
    supabase_service_role_key: str | None = None
    supabase_jwks_url: str | None = None
    session_secret: str | None = None
    environment: str = "development"
    app_name: str = "Mi Web"
    debug: bool = False
    secret_key: str = "cambia_esto_por_una_clave_larga_y_segura"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()