"""Logica del carrito.

Reglas de negocio:
  * Un usuario tiene un solo carrito (unique en carts.user_id).
  * El stock se valida al agregar y se vuelve a validar al crear el pedido.
  * Nadie puede tocar items de un carrito ajeno: toda query filtra por el
    carrito del user_id del JWT.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from supabase import Client

from fastapi_2026.core.config import settings
from fastapi_2026.core.exceptions import NotFoundError, StockError
from fastapi_2026.services.rpc_errors import rpc_error

_CENT = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(_CENT)


def _shipping_for(subtotal: Decimal) -> Decimal:
    """Vista previa del envio. El pedido real lo recalcula la RPC en Postgres
    con estos mismos settings, para que el numero mostrado no sea inventado."""
    threshold = _money(settings.free_shipping_threshold)
    if threshold > 0 and subtotal >= threshold:
        return Decimal("0.00")
    return _money(settings.shipping_cost)


class CartService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _cart_id(self, user_id: str) -> str | None:
        rows = (
            self.db.table("carts")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0]["id"] if rows else None

    def _empty_cart(self, cart_id: str | None = None) -> dict[str, Any]:
        return {
            "id": cart_id,
            "items": [],
            "total_items": 0,
            "subtotal": Decimal("0.00"),
            "shipping_cost": Decimal("0.00"),
            "free_shipping_threshold": _money(settings.free_shipping_threshold),
            "total": Decimal("0.00"),
        }

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def get_cart(self, user_id: str) -> dict[str, Any]:
        cart_id = self._cart_id(user_id)
        if not cart_id:
            return self._empty_cart()

        item_rows = (
            self.db.table("cart_items")
            .select("id, quantity, variant_id")
            .eq("cart_id", cart_id)
            .order("created_at")
            .execute()
            .data
            or []
        )
        if not item_rows:
            return self._empty_cart(cart_id)

        variant_ids = [row["variant_id"] for row in item_rows]
        variant_rows = (
            self.db.table("product_variants")
            .select("id, size, color, sku, stock, product_id")
            .in_("id", variant_ids)
            .execute()
            .data
            or []
        )
        variants = {row["id"]: row for row in variant_rows}

        product_ids = list({row["product_id"] for row in variant_rows})
        product_rows = (
            self.db.table("products")
            .select("id, name, price, image_url, slug")
            .in_("id", product_ids)
            .execute()
            .data
            or []
        )
        products = {row["id"]: row for row in product_rows}

        items: list[dict[str, Any]] = []
        subtotal = Decimal("0.00")
        total_items = 0

        for row in item_rows:
            variant = variants.get(row["variant_id"])
            if not variant:
                continue
            product = products.get(variant["product_id"])
            if not product:
                continue

            unit_price = _money(product["price"])
            quantity = int(row["quantity"])
            line_total = (unit_price * quantity).quantize(_CENT)
            subtotal += line_total
            total_items += quantity

            items.append(
                {
                    "id": row["id"],
                    "variant_id": variant["id"],
                    "quantity": quantity,
                    "size": variant["size"],
                    "color": variant["color"],
                    "sku": variant["sku"],
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "product_slug": product.get("slug"),
                    "image_url": product.get("image_url"),
                    "stock_available": int(variant["stock"]),
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )

        total = (subtotal + _shipping_for(subtotal)).quantize(_CENT)

        return {
            "id": cart_id,
            "items": items,
            "total_items": total_items,
            "subtotal": subtotal.quantize(_CENT),
            "shipping_cost": _shipping_for(subtotal),
            "free_shipping_threshold": _money(settings.free_shipping_threshold),
            "total": total,
        }

    # ------------------------------------------------------------------
    # Escrituras
    # ------------------------------------------------------------------
    def add_item(self, user_id: str, variant_id: str, quantity: int) -> dict[str, Any]:
        try:
            self.db.rpc(
                "add_cart_item",
                {
                    "p_user_id": user_id,
                    "p_variant_id": variant_id,
                    "p_quantity": quantity,
                },
            ).execute()
        except Exception as exc:
            raise rpc_error(exc) from exc

        return self.get_cart(user_id)

    def update_item(self, user_id: str, item_id: str, quantity: int) -> dict[str, Any]:
        cart_id = self._cart_id(user_id)
        if not cart_id:
            raise NotFoundError("El item no pertenece a tu carrito.")

        rows = (
            self.db.table("cart_items")
            .select("id, variant_id")
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise NotFoundError("El item no pertenece a tu carrito.")

        variants = (
            self.db.table("product_variants")
            .select("stock")
            .eq("id", rows[0]["variant_id"])
            .limit(1)
            .execute()
            .data
            or []
        )
        if not variants:
            raise NotFoundError("La variante del item ya no existe.")

        if quantity > int(variants[0]["stock"]):
            raise StockError(
                f"Solo quedan {variants[0]['stock']} unidades de esta variante."
            )

        (
            self.db.table("cart_items")
            .update({"quantity": quantity})
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .execute()
        )

        return self.get_cart(user_id)

    def clear_cart(self, user_id: str) -> dict[str, Any]:
        """Vacia el carrito completo.

        Es idempotente a proposito: si el usuario no tiene carrito (o ya lo
        vacio y la UI reintenta el click), devuelve un carrito vacio en vez de
        un 404. Borrar algo que ya no esta no es un error del cliente.

        Se filtra por cart_id derivado del JWT, nunca por un id del body:
        el cliente no puede vaciar el carrito de otro.
        """
        cart_id = self._cart_id(user_id)
        if not cart_id:
            return self._empty_cart()

        self.db.table("cart_items").delete().eq("cart_id", cart_id).execute()
        return self._empty_cart(cart_id)

    def remove_item(self, user_id: str, item_id: str) -> dict[str, Any]:
        cart_id = self._cart_id(user_id)
        if not cart_id:
            raise NotFoundError("El item no pertenece a tu carrito.")

        deleted = (
            self.db.table("cart_items")
            .delete()
            .eq("id", item_id)
            .eq("cart_id", cart_id)
            .execute()
            .data
            or []
        )
        if not deleted:
            raise NotFoundError("El item no pertenece a tu carrito.")

        return self.get_cart(user_id)
