from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Variables de Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str | None = None  # opcional, para admin

    # Variables generales de la app
    app_name: str = "Mi Web"
    debug: bool = False

    # Secreto para firmar cookies/sesiones (si usas cookies)
    secret_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Instancia única que importarás en toda la app
settings = Settings()