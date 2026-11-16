"""Tests de la logica del carrito: totales, envio y aislamiento por usuario."""

from __future__ import annotations

from decimal import Decimal

import pytest

from fastapi_2026.core.exceptions import NotFoundError, StockError
from fastapi_2026.services.cart import CartService


def item(item_id: str, variant_id: str, quantity: int, cart_id: str = "c1") -> dict:
    return {
        "id": item_id,
        "cart_id": cart_id,
        "variant_id": variant_id,
        "quantity": quantity,
        "created_at": f"2026-01-0{quantity}T00:00:00Z",
    }


class TestGetCart:
    def test_usuario_sin_carrito_devuelve_estructura_vacia(self, db):
        cart = CartService(db).get_cart("u-sin-carrito")
        assert cart["id"] is None
        assert cart["items"] == []
        assert cart["total_items"] == 0
        assert cart["shipping_cost"] == Decimal("0.00")
        assert cart["total"] == Decimal("0.00")
        # El umbral se informa siempre: la UI lo necesita para el texto "gratis desde".
        assert cart["free_shipping_threshold"] == Decimal("50.00")

    def test_carrito_cobra_envio_bajo_el_umbral(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1)]
        cart = CartService(db).get_cart("u1")

        assert cart["subtotal"] == Decimal("29.90")
        assert cart["shipping_cost"] == Decimal("5.00")
        assert cart["total"] == Decimal("34.90")
        assert cart["total_items"] == 1

    def test_carrito_es_gratis_al_superar_el_umbral(self, db):
        db.tables["cart_items"] = [item("ci1", "v5", 1)]  # 60.00
        cart = CartService(db).get_cart("u1")

        assert cart["subtotal"] == Decimal("60.00")
        assert cart["shipping_cost"] == Decimal("0.00")
        assert cart["total"] == Decimal("60.00")

    def test_suma_varias_lineas_y_cantidades(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1), item("ci2", "v3", 2)]
        cart = CartService(db).get_cart("u1")

        assert cart["total_items"] == 3
        assert cart["subtotal"] == Decimal("68.90")
        assert cart["total"] == Decimal("68.90")
        assert len(cart["items"]) == 2
        assert cart["items"][0]["line_total"] == Decimal("29.90")
        assert cart["items"][1]["line_total"] == Decimal("39.00")

    def test_item_de_otro_carrito_no_se_mezcla(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1, cart_id="c-otro")]
        cart = CartService(db).get_cart("u1")
        assert cart["items"] == []
        assert cart["subtotal"] == Decimal("0.00")

    def test_precio_sale_del_catalogo_no_del_cliente(self, db):
        """El carrito no guarda precios: se leen de products en cada consulta."""
        db.tables["cart_items"] = [item("ci1", "v1", 1)]
        assert CartService(db).get_cart("u1")["items"][0]["unit_price"] == Decimal("29.90")

        db.tables["products"][0]["price"] = 25.00
        assert CartService(db).get_cart("u1")["items"][0]["unit_price"] == Decimal("25.00")

    def test_el_item_trae_el_slug_para_enlazar_al_detalle(self, db):
        """La pagina de carrito enlaza a /tienda/{slug}, no a /tienda/{id}."""
        db.tables["cart_items"] = [item("ci1", "v1", 1)]
        assert (
            CartService(db).get_cart("u1")["items"][0]["product_slug"]
            == "camisa-oxford-azul"
        )


class TestClearCart:
    def test_vaciar_carrito_con_items(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1), item("ci2", "v3", 1)]
        cart = CartService(db).clear_cart("u1")

        assert cart["items"] == []
        assert cart["total"] == Decimal("0.00")
        assert db.tables["cart_items"] == []

    def test_vaciar_es_idempotente_sin_carrito(self, db):
        cart = CartService(db).clear_cart("u-sin-carrito")
        assert cart["items"] == []
        assert cart["id"] is None

    def test_vaciar_no_toca_el_carrito_de_otro_usuario(self, db):
        db.tables["carts"].append({"id": "c2", "user_id": "u2"})
        db.tables["cart_items"] = [item("ci1", "v1", 1), item("ci2", "v1", 1, cart_id="c2")]

        CartService(db).clear_cart("u1")

        restantes = [i for i in db.tables["cart_items"] if i["cart_id"] == "c2"]
        assert len(restantes) == 1


class TestUpdateItem:
    def test_no_puedo_editar_item_ajeno(self, db):
        db.tables["cart_items"] = [item("ci9", "v1", 1, cart_id="c-otro")]
        with pytest.raises(NotFoundError):
            CartService(db).update_item("u1", "ci9", 2)

    def test_cantidad_por_encima_del_stock(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1)]  # stock 8
        with pytest.raises(StockError) as exc:
            CartService(db).update_item("u1", "ci1", 9)
        assert "8" in str(exc.value.message)

    def test_cantidad_valida_actualiza_la_linea(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1)]
        cart = CartService(db).update_item("u1", "ci1", 2)

        assert cart["items"][0]["quantity"] == 2
        assert cart["subtotal"] == Decimal("59.80")


class TestAddItem:
    def test_delega_en_la_rpc_con_el_usuario_del_jwt(self, db):
        capturado = {}

        def handler(params):
            capturado.update(params)
            return None

        db.rpc_handlers["add_cart_item"] = handler
        CartService(db).add_item("u1", "v1", 2)

        assert capturado == {"p_user_id": "u1", "p_variant_id": "v1", "p_quantity": 2}

    def test_error_de_stock_de_la_rpc_se_traduce(self, db):
        def handler(params):
            raise Exception("P0001: STOCK_INSUFICIENTE: Camisa Oxford Azul")

        db.rpc_handlers["add_cart_item"] = handler
        with pytest.raises(StockError):
            CartService(db).add_item("u1", "v1", 2)


class TestRemoveItem:
    def test_no_puedo_borrar_item_ajeno(self, db):
        db.tables["cart_items"] = [item("ci9", "v1", 1, cart_id="c-otro")]
        with pytest.raises(NotFoundError):
            CartService(db).remove_item("u1", "ci9")

    def test_borrar_item_propio(self, db):
        db.tables["cart_items"] = [item("ci1", "v1", 1)]
        cart = CartService(db).remove_item("u1", "ci1")
        assert cart["items"] == []
