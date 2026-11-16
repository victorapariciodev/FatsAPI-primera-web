"""Logica de pedidos (sin cobro: el MVP no procesa pagos).

Crear el pedido NO se implementa con varias llamadas HTTP: se delega en la
funcion ``place_order`` de Postgres para que la validacion de stock, la
creacion del pedido y la resta de inventario ocurran en una sola transaccion
(atomica). Igual con ``cancel_order``: cancelar y devolver stock es un paso.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from supabase import Client

from fastapi_2026.core.config import settings
from fastapi_2026.core.exceptions import NotFoundError
from fastapi_2026.services.rpc_errors import rpc_error

ORDER_SELECT = "*, order_items(*)"


class OrderService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_order(row: dict[str, Any]) -> dict[str, Any]:
        order = dict(row)
        order["items"] = order.pop("order_items", None) or []
        return order

    @staticmethod
    def _rpc_payload(response: Any) -> dict[str, Any]:
        data = getattr(response, "data", None)
        if isinstance(data, list):
            return data[0] if data else {}
        return data or {}

    # ------------------------------------------------------------------
    # Crear pedido a partir del carrito
    # ------------------------------------------------------------------
    def place_order(self, user_id: str, shipping_address: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.db.rpc(
                "place_order",
                {
                    "p_user_id": user_id,
                    "p_shipping_address": shipping_address,
                    "p_shipping_cost": float(settings.shipping_cost),
                    "p_free_shipping_threshold": float(settings.free_shipping_threshold),
                },
            ).execute()
        except Exception as exc:
            raise rpc_error(exc) from exc

        payload = self._rpc_payload(response)
        order_id = payload.get("order_id")
        if not order_id:
            raise NotFoundError("No se pudo generar el pedido.")

        return self.get_order(user_id, order_id)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def list_orders(self, user_id: str, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        start = (page - 1) * page_size
        response = (
            self.db.table("orders")
            .select(ORDER_SELECT, count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(start, start + page_size - 1)
            .execute()
        )
        rows = response.data or []
        return {
            "items": [self._normalize_order(row) for row in rows],
            "total": response.count or 0,
        }

    def get_order(self, user_id: str, order_id: str) -> dict[str, Any]:
        rows = (
            self.db.table("orders")
            .select(ORDER_SELECT)
            .eq("id", order_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise NotFoundError("La orden no existe o no te pertenece.")
        return self._normalize_order(rows[0])

    # ------------------------------------------------------------------
    # Cancelacion
    # ------------------------------------------------------------------
    def cancel_order(self, user_id: str, order_id: str) -> dict[str, Any]:
        try:
            self.db.rpc(
                "cancel_order",
                {"p_user_id": user_id, "p_order_id": order_id},
            ).execute()
        except Exception as exc:
            raise rpc_error(exc) from exc

        return self.get_order(user_id, order_id)
