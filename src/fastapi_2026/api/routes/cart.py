"""Endpoints del carrito. Todos requieren sesion valida."""

from typing import Any

from fastapi import APIRouter, Depends
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import get_current_user
from fastapi_2026.schemas.cart import CartItemCreate, CartItemUpdate, CartOut
from fastapi_2026.services.cart import CartService

router = APIRouter(prefix="/api/cart", tags=["Carrito"])


@router.get("", response_model=CartOut, summary="Ver mi carrito")
def get_cart(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return CartService(db).get_cart(user["sub"])


@router.post(
    "/items",
    response_model=CartOut,
    summary="Agregar variante al carrito (suma cantidad si ya existe)",
)
def add_item(
    payload: CartItemCreate,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return CartService(db).add_item(user["sub"], payload.variant_id, payload.quantity)


@router.patch(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Cambiar cantidad de un item",
)
def update_item(
    item_id: str,
    payload: CartItemUpdate,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return CartService(db).update_item(user["sub"], item_id, payload.quantity)


@router.delete(
    "",
    response_model=CartOut,
    summary="Vaciar el carrito completo",
)
def clear_cart(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return CartService(db).clear_cart(user["sub"])


@router.delete(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Quitar un item del carrito",
)
def remove_item(
    item_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return CartService(db).remove_item(user["sub"], item_id)
