from supabase import create_client, Client
from fastapi_2026.core.config import settings  # <-- Importación ajustada a tu estructura

supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)git 