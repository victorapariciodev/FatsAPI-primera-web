from pathlib import Path  # <-- Agrega esta importación
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi_2026.core.templates import templates
from fastapi_2026.api.routes import pages, auth, profile 

app = FastAPI()

# Calculamos la ruta absoluta a la carpeta static
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

from pathlib import Path
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# ✅ Un solo mount
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Incluir Routers
app.include_router(pages.router)
app.include_router(auth.router)

# Manejo global de errores 401
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and not request.url.path.startswith("/api"):
        return RedirectResponse(url="/login", status_code=303)
    
    from fastapi.exception_handlers import http_exception_handler
    return await http_exception_handler(request, exc)
app.include_router(profile.router)