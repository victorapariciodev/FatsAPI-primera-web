from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fastapi_2026.core.error_handlers import register_error_handlers
from fastapi_2026.api.routes import (
    auth,
    cart,
    health,
    orders,
    pages,
    products,
    profile,
    store_pages,
)

app = FastAPI(title="Tienda de ropa")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Las URLs de imagen guardadas en productos usan /static/img.
app.mount(
    "/static/img",
    StaticFiles(directory=STATIC_DIR / "images"),
    name="product_images",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Routers
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(products.router)
app.include_router(products.admin_router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(store_pages.router)
app.include_router(health.router)

# Errores de dominio -> JSON con su status correcto
register_error_handlers(app)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and not request.url.path.startswith("/api"):
        return RedirectResponse(url="/login", status_code=303)

    from fastapi.exception_handlers import http_exception_handler

    return await http_exception_handler(request, exc)
