"""Endpoints del catalogo de ropa.

Rutas publicas (catalogo) y rutas de administracion protegidas por rol.
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import require_admin
from fastapi_2026.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductPage,
    ProductUpdate,
    StockUpdate,
    VariantOut,
)
from fastapi_2026.services.product import ProductService

router = APIRouter(prefix="/api/products", tags=["Productos"])


@router.get("", response_model=ProductPage, summary="Listar catalogo (publico)")
def list_products(
    category: str | None = Query(default=None, description="Ej: camisas, franelas"),
    search: str | None = Query(default=None, max_length=80, description="Busqueda por nombre"),
    size: str | None = Query(default=None, description="Talla exacta: S, M, L, XL, 30, 32..."),
    in_stock: bool = Query(default=False, description="Solo productos con al menos una variante en stock"),
    sort: str = Query(
        default="newest",
        pattern="^(newest|price_asc|price_desc)$",
        description="newest | price_asc | price_desc",
    ),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_price no puede ser mayor que max_price.",
        )

    return ProductService(db).list_products(
        category=category,
        search=search,
        size=size,
        in_stock=in_stock,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        page_size=page_size,
    )


# OJO: esta ruta va ANTES de /{product_id}. Si la declaras despues, FastAPI
# intenta castear "categories" a UUID y devuelve 422.
@router.get("/categories", response_model=list[str], summary="Categorias disponibles")
def list_categories(db: Client = Depends(get_db)) -> list[str]:
    return ProductService(db).list_categories()


@router.get("/{product_id}", response_model=ProductOut, summary="Detalle de producto")
def get_product(product_id: str, db: Client = Depends(get_db)) -> dict[str, Any]:
    return ProductService(db).get_product(product_id)


@router.get(
    "/by-slug/{slug}",
    response_model=ProductOut,
    summary="Detalle de producto por slug (URL amigable)",
)
def get_product_by_slug(slug: str, db: Client = Depends(get_db)) -> dict[str, Any]:
    return ProductService(db).get_product_by_slug(slug)


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto con sus variantes (admin)",
)
def create_product(
    payload: ProductCreate,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True)
    return ProductService(db).create_product(data)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    summary="Actualizar datos del producto (admin)",
)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    # exclude_unset evita sobrescribir con None campos que no se enviaron.
    data = payload.model_dump(exclude_unset=True)
    return ProductService(db).update_product(product_id, data)


@router.patch(
    "/{product_id}/variants/{variant_id}/stock",
    response_model=VariantOut,
    summary="Reponer stock de una variante (admin)",
)
def update_variant_stock(
    product_id: str,
    variant_id: str,
    payload: StockUpdate,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    return ProductService(db).update_variant_stock(product_id, variant_id, payload.stock)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar producto - borrado logico (admin)",
)
def deactivate_product(
    product_id: str,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> Response:
    ProductService(db).deactivate_product(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------
# Panel admin: misma logica, pero incluye productos desactivados.
# ---------------------------------------------------------------------
admin_router = APIRouter(prefix="/api/admin", tags=["Admin"])


@admin_router.get(
    "/products",
    response_model=ProductPage,
    summary="Listar productos incluyendo inactivos (admin)",
)
def list_all_products(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    return ProductService(db).list_products(
        category=category,
        search=search,
        page=page,
        page_size=page_size,
        include_inactive=True,
    )
