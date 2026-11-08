# src/fastapi_2026/services/profile.py
from supabase import Client

class ProfileService:
    def __init__(self, db: Client):
        self.db = db

    def save_employment(self, user_id: str, data: dict):
        try:
            data['profile_id'] = user_id
            # .upsert() inserta o actualiza si el profile_id ya existe
            response = self.db.table('employment_details').upsert(data).execute()
            return response.data
        except Exception as e:
            print(f"Error guardando empleo: {e}")
            raise

    def save_education(self, user_id: str, data: dict):
        try:
            data['profile_id'] = user_id
            response = self.db.table('education_records').upsert(data).execute()
            return response.data
        except Exception as e:
            print(f"Error guardando estudios: {e}")
            raise

    def save_banking(self, user_id: str, data: dict):
        try:
            data['profile_id'] = user_id
            response = self.db.table('banking_info').upsert(data).execute()
            return response.data
        except Exception as e:
            print(f"Error guardando banco: {e}")
            raise