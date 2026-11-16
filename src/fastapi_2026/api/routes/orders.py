"""Endpoints de pedidos: crear pedido desde el carrito, historial y cancelacion.

Sin pasarela de pago: el pedido se registra en estado 'pending' (por despachar).
"""

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import get_current_user
from fastapi_2026.schemas.order import OrderCreate, OrderOut, OrderPage
from fastapi_2026.services.order import OrderService

router = APIRouter(prefix="/api/orders", tags=["Pedidos"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido a partir del carrito (atomico, sin cobro)",
)
def place_order(
    payload: OrderCreate,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return OrderService(db).place_order(
        user["sub"], payload.shipping_address.model_dump()
    )


@router.get("", response_model=OrderPage, summary="Mi historial de pedidos")
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return OrderService(db).list_orders(user["sub"], page=page, page_size=page_size)


@router.get("/{order_id}", response_model=OrderOut, summary="Detalle de un pedido")
def get_order(
    order_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return OrderService(db).get_order(user["sub"], order_id)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderOut,
    summary="Cancelar pedido pendiente y devolver stock",
)
def cancel_order(
    order_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return OrderService(db).cancel_order(user["sub"], order_id)
