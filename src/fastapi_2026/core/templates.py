# src/fastapi_2026/core/templates.py
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Resolvemos la ruta UNA SOLA VEZ para todo el proyecto
# core/templates.py -> parent (core) -> parent (fastapi_2026)
BASE_DIR = Path(__file__).resolve().parent.parent

# Instancia global
templates = Jinja2Templates(directory=BASE_DIR / "templates")