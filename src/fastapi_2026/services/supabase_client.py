# src/fastapi_2026/services/supabase_client.py
from supabase import create_client, Client
from fastapi_2026.core.config import settings

supabase: Client = create_client(
    settings.supabase_url, 
    settings.supabase_publishable_key # <-- Usando la nueva variable
)