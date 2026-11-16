"""Tests de pedidos: atomizacion delegada a Postgres y traduccion de errores."""

from __future__ import annotations

import pytest

from fastapi_2026.core.config import settings
from fastapi_2026.core.exceptions import (
    DomainError,
    InvalidOperation,
    NotFoundError,
    StockError,
)
from fastapi_2026.services.order import OrderService

DIRECCION = {
    "full_name": "Alex Mercer",
    "phone": "+58 412 000-0000",
    "address_line": "Av. Principal Los Cortijos",
    "city": "Caracas",
    "state": "Distrito Capital",
    "postal_code": "1071",
    "country": "VE",
}


class TestPlaceOrder:
    def test_pasa_envio_y_umbral_desde_settings(self, db):
        capturado = {}

        def handler(params):
            capturado.update(params)
            return [{"order_id": "o1"}]

        db.rpc_handlers["place_order"] = handler
        OrderService(db).place_order("u1", DIRECCION)

        assert capturado["p_user_id"] == "u1"
        assert capturado["p_shipping_address"] == DIRECCION
        assert capturado["p_shipping_cost"] == float(settings.shipping_cost)
        assert capturado["p_free_shipping_threshold"] == float(
            settings.free_shipping_threshold
        )

    def test_devuelve_el_pedido_con_sus_items(self, db):
        db.rpc_handlers["place_order"] = lambda params: [{"order_id": "o1"}]
        order = OrderService(db).place_order("u1", DIRECCION)

        assert order["id"] == "o1"
        assert "order_items" not in order
        assert order["items"][0]["product_name"] == "Camisa Oxford Azul"

    def test_sin_order_id_es_error(self, db):
        db.rpc_handlers["place_order"] = lambda params: [{}]
        with pytest.raises(NotFoundError):
            OrderService(db).place_order("u1", DIRECCION)

    def test_error_de_stock_se_traduce(self, db):
        def handler(params):
            raise Exception("P0001: STOCK_INSUFICIENTE: Camisa Oxford Azul")

        db.rpc_handlers["place_order"] = handler
        with pytest.raises(StockError):
            OrderService(db).place_order("u1", DIRECCION)

    def test_carrito_vacio_se_traduce(self, db):
        def handler(params):
            raise Exception("P0001: CARRITO_VACIO")

        db.rpc_handlers["place_order"] = handler
        with pytest.raises(InvalidOperation) as exc:
            OrderService(db).place_order("u1", DIRECCION)

        assert exc.value.status_code == 409
        assert exc.value.code == "invalid_operation"

    def test_producto_desactivado_incluye_el_nombre(self, db):
        def handler(params):
            raise Exception("P0001: PRODUCTO_NO_DISPONIBLE: Franela Negra")

        db.rpc_handlers["place_order"] = handler
        with pytest.raises(InvalidOperation) as exc:
            OrderService(db).place_order("u1", DIRECCION)

        assert "Franela Negra" in exc.value.message

    def test_error_desconocido_cae_en_domain_error(self, db):
        def handler(params):
            raise Exception("lagartija inesperada")

        db.rpc_handlers["place_order"] = handler
        with pytest.raises(DomainError) as exc:
            OrderService(db).place_order("u1", DIRECCION)

        assert exc.value.status_code == 400

    def test_el_mensaje_de_stock_no_repite_el_codigo(self, db):
        """Regresion: con 'P0001: STOCK_INSUFICIENTE: X' el detalle salia
        como 'Producto: STOCK_INSUFICIENTE: X'."""

        def handler(params):
            raise Exception("P0001: STOCK_INSUFICIENTE: Camisa Oxford Azul")

        db.rpc_handlers["place_order"] = handler
        with pytest.raises(StockError) as exc:
            OrderService(db).place_order("u1", DIRECCION)

        assert "Producto: Camisa Oxford Azul." in exc.value.message
        assert "STOCK_INSUFICIENTE" not in exc.value.message

    def test_el_nombre_del_producto_desactivado_sale_limpio(self, db):
        def handler(params):
            raise Exception("P0001: PRODUCTO_NO_DISPONIBLE: Franela Negra")

        db.rpc_handlers["place_order"] = handler
        with pytest.raises(InvalidOperation) as exc:
            OrderService(db).place_order("u1", DIRECCION)

        assert exc.value.message == "El producto 'Franela Negra' ya no esta disponible."


class TestListAndGet:
    def test_historial_solo_del_usuario_autenticado(self, db):
        result = OrderService(db).list_orders("u1")
        assert [o["id"] for o in result["items"]] == ["o1"]
        assert result["total"] == 1

    def test_pedido_de_otro_usuario_es_404(self, db):
        with pytest.raises(NotFoundError):
            OrderService(db).get_order("u1", "o2")

    def test_pedido_inexistente_es_404(self, db):
        with pytest.raises(NotFoundError):
            OrderService(db).get_order("u1", "no-existe")


class TestCancel:
    def test_pasa_user_y_order_a_la_rpc(self, db):
        capturado = {}

        def handler(params):
            capturado.update(params)
            return None

        db.rpc_handlers["cancel_order"] = handler
        OrderService(db).cancel_order("u1", "o1")

        assert capturado == {"p_user_id": "u1", "p_order_id": "o1"}

    def test_orden_no_cancelable_se_traduce(self, db):
        def handler(params):
            raise Exception("P0001: ORDEN_NO_CANCELABLE")

        db.rpc_handlers["cancel_order"] = handler
        with pytest.raises(InvalidOperation) as exc:
            OrderService(db).cancel_order("u1", "o1")

        assert "pending" in exc.value.message
