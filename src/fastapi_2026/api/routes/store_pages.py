"""Paginas HTML de la tienda.

Estas rutas NO contienen logica de negocio: leen con los MISMOS servicios que
usan los endpoints ``/api/*`` y entregan el contexto ya calculado a Jinja.
Es deliberado: la regla vive una sola vez en ``services/`` y existen dos
transportes (JSON y HTML). Si manana cambia el calculo del envio, cambia en
``CartService`` y las dos caras de la tienda se enteran solas.
"""

from __future__ import annotations

import math
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BeforeValidator
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import get_optional_user, user_is_admin
from fastapi_2026.core.exceptions import DomainError, NotFoundError
from fastapi_2026.core.templates import templates
from fastapi_2026.services.cart import CartService
from fastapi_2026.services.order import OrderService
from fastapi_2026.services.product import ProductService

router = APIRouter(tags=["Tienda (páginas)"])

CATALOG_PAGE_SIZE = 12
ORDERS_PAGE_SIZE = 10
ADMIN_PAGE_SIZE = 50

# Lista blanca: la pagina coacciona el orden en vez de reventar con 422 como
# hace la API. Un query param basura no debe romper una vista publica.
_SORTS = {"newest", "price_asc", "price_desc"}


def _blank_price_as_none(value: Any) -> Any:
    return None if value == "" else value


OptionalPrice = Annotated[float | None, BeforeValidator(_blank_price_as_none)]


def _to_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def _context(user: Optional[dict], db: Client, **extra: Any) -> dict[str, Any]:
    """Contexto comun del layout (header, contador del carrito, rol).

    El contador se calcula con el servicio real, no se lee de una cookie: si
    el usuario edita la cookie, el badge miente pero el carrito no.
    """
    cart_count = 0
    if user:
        try:
            cart_count = CartService(db).get_cart(user["sub"])["total_items"]
        except DomainError:
            # Un carrito roto no debe tumbar una pagina de catalogo.
            cart_count = 0

    context: dict[str, Any] = {
        "usuario": user,
        "es_admin": user_is_admin(user),
        "cart_count": cart_count,
        "filtros": {},
    }
    context.update(extra)
    return context


# ----------------------------------------------------------------------
# Catalogo
# ----------------------------------------------------------------------
@router.get("/tienda", summary="Catalogo de la tienda (HTML)")
def catalogo(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    size: str | None = None,
    min_price: OptionalPrice = None,
    max_price: OptionalPrice = None,
    sort: str = "newest",
    in_stock: bool = False,
    page: int = Query(default=1, ge=1),
    db: Client = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
) -> Any:
    servicio = ProductService(db)
    orden = sort if sort in _SORTS else "newest"

    productos = servicio.list_products(
        category=category or None,
        search=(q or "").strip() or None,
        size=size or None,
        in_stock=in_stock,
        min_price=min_price,
        max_price=max_price,
        sort=orden,
        page=page,
        page_size=CATALOG_PAGE_SIZE,
    )

    return templates.TemplateResponse(
        request=request,
        name="store/catalogo.html",
        context=_context(
            user,
            db,
            productos=productos,
            categorias=servicio.list_categories(),
            # Solo tallas comprables: no se pinta un chip que lleva a un
            # callejon sin salida.
            tallas=servicio.list_sizes(),
            filtros={
                "q": q,
                "category": category,
                "size": size,
                "min_price": min_price,
                "max_price": max_price,
                "sort": orden,
                "in_stock": in_stock,
            },
        ),
    )


@router.get("/tienda/{slug}", summary="Detalle de producto (HTML)")
def producto(
    slug: str,
    request: Request,
    size: str | None = None,
    db: Client = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
) -> Any:
    servicio = ProductService(db)

    try:
        item = servicio.get_product_by_slug(slug)
    except NotFoundError:
        # Un slug muerto no es una pagina: se devuelve al catalogo en vez de
        # escupir un JSON de error dentro del navegador.
        return RedirectResponse(
            url="/tienda", status_code=status.HTTP_303_SEE_OTHER
        )

    variantes = item["variants"]

    # Los chips de talla de la tarjeta llegan como ?size=M. Se preselecciona
    # esa talla SI tiene stock; si esta agotada se cae en la primera
    # disponible. Nunca se preselecciona algo que no se puede comprar.
    pedida = size.upper() if size else None
    inicial = next(
        (
            v
            for v in variantes
            if pedida and str(v.get("size", "")).upper() == pedida and int(v.get("stock") or 0) > 0
        ),
        None,
    )
    if inicial is None:
        inicial = next(
            (v for v in variantes if int(v.get("stock") or 0) > 0),
            None,
        )

    return templates.TemplateResponse(
        request=request,
        name="store/producto.html",
        context=_context(
            user,
            db,
            producto=item,
            variantes=variantes,
            # La talla preseleccionada es comprable: el servidor y el JS
            # arrancan mostrando exactamente lo mismo.
            variante_inicial=inicial,
            colores=sorted({str(v["color"]) for v in variantes if v.get("color")}),
            stock_inicial=int((inicial or {}).get("stock") or 0),
        ),
    )


# ----------------------------------------------------------------------
# Carrito y compra
# ----------------------------------------------------------------------
@router.get("/carrito", summary="Carrito (HTML)")
def carrito(
    request: Request,
    db: Client = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
) -> Any:
    if not user:
        return _to_login()

    return templates.TemplateResponse(
        request=request,
        name="store/carrito.html",
        context=_context(user, db, carrito=CartService(db).get_cart(user["sub"])),
    )


@router.get("/pedido/confirmar", summary="Confirmar pedido (HTML)")
def confirmar(
    request: Request,
    db: Client = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
) -> Any:
    if not user:
        return _to_login()

    carrito_actual = CartService(db).get_cart(user["sub"])
    if not carrito_actual["items"]:
        # Confirmar un carrito vacio no tiene sentido: la RPC lo rechazaria
        # con CARRITO_VACIO. Mejor devolverlo al carrito que mostrar un error.
        return RedirectResponse(
            url="/carrito", status_code=status.HTTP_303_SEE_OTHER
        )

    return templates.TemplateResponse(
        request=request,
        name="store/confirmar.html",
        context=_context(user, db, carrito=carrito_actual),
    )


@router.get("/pedidos", summary="Mi historial de pedidos (HTML)")
def pedidos(
    request: Request,
    page: int = Query(default=1, ge=1),
    db: Client = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
) -> Any:
    if not user:
        return _to_login()

    historial = OrderService(db).list_orders(
        user["sub"], page=page, page_size=ORDERS_PAGE_SIZE
    )
    historial["page"] = page
    historial["pages"] = (
        math.ceil(historial["total"] / ORDERS_PAGE_SIZE) if historial["total"] else 0
    )

    return templates.TemplateResponse(
        request=request,
        name="store/pedidos.html",
        context=_context(user, db, pedidos=historial),
    )


# ----------------------------------------------------------------------
# Administracion
# ----------------------------------------------------------------------
@router.get("/admin/productos", summary="Gestion de productos (HTML, admin)")
def admin_productos(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    page: int = Query(default=1, ge=1),
    db: Client = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
) -> Any:
    if not user:
        return _to_login()

    if not user_is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador.",
        )

    servicio = ProductService(db)
    productos = servicio.list_products(
        category=category or None,
        search=(q or "").strip() or None,
        include_inactive=include_inactive,
        page=page,
        page_size=ADMIN_PAGE_SIZE,
    )

    return templates.TemplateResponse(
        request=request,
        name="store/admin_productos.html",
        context=_context(
            user,
            db,
            productos=productos,
            categorias=servicio.list_categories(),
            inactivos=servicio.count_inactive(),
            filtros={
                "q": q,
                "category": category,
                "include_inactive": include_inactive,
            },
        ),
    )
