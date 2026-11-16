"""Smoke test contra el Supabase REAL.

A diferencia de pytest, este script ESCRIBE en la base: por eso no vive en
``tests/``. Crea un usuario y un producto temporales, recorre la compra
completa (carrito -> pedido -> cancelacion), verifica el stock en cada paso y
limpia absolutamente todo al final, aunque haya fallado a mitad de camino.

Uso:
    uv run python scripts/smoke_real.py

Codigos de salida:
    0  todo el flujo funciona contra la base real
    1  la base no esta lista o algun paso fallo (imprime la causa)
"""

from __future__ import annotations

import sys
from decimal import Decimal
from uuid import uuid4

from fastapi_2026.api.db import get_db
from fastapi_2026.core.config import settings
from fastapi_2026.services.cart import CartService
from fastapi_2026.services.health import check_database
from fastapi_2026.services.order import OrderService
from fastapi_2026.services.product import ProductService

DIRECCION = {
    "full_name": "Smoke Test",
    "phone": "+58 412 000-0000",
    "address_line": "Av. Smoke 123, Piso 1",
    "city": "Caracas",
    "state": "Distrito Capital",
    "postal_code": "1010",
    "country": "VE",
}

PASOS: list[tuple[str, bool]] = []


def paso(nombre: str, ok: bool) -> None:
    PASOS.append((nombre, ok))
    print(f"  {'OK ' if ok else 'FALLA'}  {nombre}")


def dinero(valor: object) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def main() -> int:
    print("== 1. Diagnostico del esquema ==")
    db = get_db()

    reporte = check_database(db)
    for check in reporte["checks"]:
        if not check["ok"]:
            print(f"  FALLA  tabla {check['tabla']}: {check['detalle']}")

    if not reporte["ok"]:
        print(f"\nLa base no esta lista: {reporte['sugerencia']}")
        return 1
    print(f"  OK     {reporte['tablas_ok']}/{reporte['tablas_total']} tablas responden\n")

    sufijo = uuid4().hex[:8]
    user_id: str | None = None
    product_id: str | None = None
    order_id: str | None = None

    try:
        print("== 2. Preparar datos temporales ==")
        creado = db.auth.admin.create_user(
            {
                "email": f"smoke-{sufijo}@nightkids.invalid",
                "password": f"Smoke-{sufijo}-123456!",
                "email_confirm": True,
            }
        )
        user_id = creado.user.id
        paso(f"usuario temporal {user_id[:8]}...", True)

        producto = ProductService(db).create_product(
            {
                "name": f"Smoke {sufijo}",
                "category": "smoke",
                "price": Decimal("10.00"),
                "description": "Producto temporal del smoke test.",
                "variants": [
                    {
                        "size": "M",
                        "color": "gris",
                        "sku": f"SMK-{sufijo}",
                        "stock": 3,
                    }
                ],
            }
        )
        product_id = producto["id"]
        variante_id = producto["variants"][0]["id"]
        paso(f"producto temporal {producto['slug']}", True)

        print("\n== 3. Carrito ==")
        carrito = CartService(db).add_item(user_id, variante_id, 2)
        paso("add_cart_item valida y agrega 2 unidades", carrito["total_items"] == 2)
        paso(
            f"subtotal calculado por el servidor = {carrito['subtotal']}",
            dinero(carrito["subtotal"]) == Decimal("20.00"),
        )

        print("\n== 4. Pedido ==")
        pedido = OrderService(db).place_order(user_id, DIRECCION)
        order_id = pedido["id"]
        paso(f"place_order creo el pedido {order_id[:8]}...", bool(order_id))
        paso("nace en estado pending (sin pago)", pedido["status"] == "pending")
        paso(
            "copia el snapshot del item",
            len(pedido["items"]) == 1
            and pedido["items"][0]["product_name"] == producto["name"],
        )
        paso(
            f"subtotal {pedido['subtotal']} + envio {pedido['shipping_cost']}",
            dinero(pedido["subtotal"]) == Decimal("20.00")
            and dinero(pedido["shipping_cost"]) == dinero(settings.shipping_cost),
        )
        paso(
            "total = 20.00 de mercancia + envio 5.00",
            dinero(pedido["total"]) == Decimal("25.00"),
        )

        stock_tras_compra = ProductService(db).get_product(product_id)["variants"][0]["stock"]
        paso(f"el stock bajo de 3 a {stock_tras_compra}", stock_tras_compra == 1)

        carrito_vacio = CartService(db).get_cart(user_id)
        paso("el carrito quedo vacio tras la compra", carrito_vacio["items"] == [])

        print("\n== 5. Cancelacion ==")
        cancelado = OrderService(db).cancel_order(user_id, order_id)
        paso("cancel_order marca cancelled", cancelado["status"] == "cancelled")

        stock_devuelto = ProductService(db).get_product(product_id)["variants"][0]["stock"]
        paso(f"el stock volvio a {stock_devuelto}", stock_devuelto == 3)

        try:
            OrderService(db).cancel_order(user_id, order_id)
            paso("cancelar dos veces debe fallar", False)
        except Exception:
            paso("cancelar dos veces se rechaza (ORDEN_NO_CANCELABLE)", True)

    except Exception as exc:  # noqa: BLE001 - el script reporta, no explota
        print(f"\nFALLO: {type(exc).__name__}: {str(exc)[:400]}")
        return 1

    finally:
        print("\n== 6. Limpieza ==")
        if user_id:
            try:
                # Borra en cascada carrito, items, pedidos y order_items.
                db.auth.admin.delete_user(user_id)
                paso("usuario temporal eliminado (cascade)", True)
            except Exception as exc:  # noqa: BLE001
                paso(f"no se pudo borrar el usuario: {exc}", False)
        if product_id:
            try:
                if order_id:
                    db.table("orders").delete().eq("id", order_id).execute()
                db.table("products").delete().eq("id", product_id).execute()
                paso("producto temporal eliminado", True)
            except Exception as exc:  # noqa: BLE001
                paso(f"no se pudo borrar el producto: {exc}", False)

    fallos = [nombre for nombre, ok in PASOS if not ok]
    print("\n" + "=" * 60)
    if fallos:
        print(f"RESULTADO: {len(fallos)} paso(s) fallaron")
        for nombre in fallos:
            print("  -", nombre)
        return 1

    print(f"RESULTADO: {len(PASOS)} pasos OK contra la base real")
    return 0


if __name__ == "__main__":
    sys.exit(main())
