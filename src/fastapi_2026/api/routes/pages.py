from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
#from api.deps import obtener_usuario_actual

router = APIRouter()
#@router.get("/", response_class=HTMLResponse)
#async def landing(request: Request):
#    return templates.TemplateResponse(request=request, name="landing.html")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/menu", response_class=HTMLResponse)
async def menu(request: Request):
    # Aquí podrías obtener el usuario de la sesión y pasarlo al contexto
    return templates.TemplateResponse(request=request, name="menu.html")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "titulo": "Mi sexo web con FastAPI",
            "mensaje": "¡Hola desde una plantilla con CSS!",
        },
    )