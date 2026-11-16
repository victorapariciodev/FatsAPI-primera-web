"""Tests de la capa HTTP de carrito y pedidos."""

from __future__ import annotations

DIRECCION = {
    "full_name": "Alex Mercer",
    "phone": "+58 412 000-0000",
    "address_line": "Av. Principal Los Cortijos",
    "city": "Caracas",
    "state": "Distrito Capital",
    "postal_code": "1071",
    "country": "VE",
}


class TestCarritoHTTP:
    def test_sin_sesion_es_401_json(self, anon_client):
        response = anon_client.get("/api/cart")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_carrito_vacio_trae_envio_y_umbral(self, client):
        body = client.get("/api/cart").json()

        assert body["items"] == []
        assert body["total_items"] == 0
        assert body["shipping_cost"] == "0.00"
        assert body["free_shipping_threshold"] == "50.00"
        assert body["total"] == "0.00"

    def test_vaciar_carrito(self, client, db):
        db.tables["cart_items"] = [
            {"id": "ci1", "cart_id": "c1", "variant_id": "v1", "quantity": 2, "created_at": "1"}
        ]

        response = client.delete("/api/cart")
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert db.tables["cart_items"] == []

    def test_vaciar_carrito_es_idempotente(self, client):
        assert client.delete("/api/cart").status_code == 200
        assert client.delete("/api/cart").status_code == 200

    def test_agregar_item_usa_el_usuario_del_jwt(self, client, db):
        capturado = {}

        def handler(params):
            capturado.update(params)
            return None

        db.rpc_handlers["add_cart_item"] = handler
        response = client.post("/api/cart/items", json={"variant_id": "v1", "quantity": 2})

        assert response.status_code == 200
        assert capturado["p_user_id"] == "u1"
        assert capturado["p_quantity"] == 2

    def test_cantidad_cero_es_422(self, client):
        response = client.post("/api/cart/items", json={"variant_id": "v1", "quantity": 0})
        assert response.status_code == 422

    def test_cantidad_mayor_a_20_es_422(self, client):
        response = client.post("/api/cart/items", json={"variant_id": "v1", "quantity": 21})
        assert response.status_code == 422

    def test_editar_item_ajeno_es_404(self, client, db):
        db.tables["cart_items"] = [
            {"id": "ci9", "cart_id": "c-otro", "variant_id": "v1", "quantity": 1, "created_at": "1"}
        ]
        response = client.patch("/api/cart/items/ci9", json={"quantity": 2})
        assert response.status_code == 404

    def test_quitar_item_ajeno_es_404(self, client, db):
        db.tables["cart_items"] = [
            {"id": "ci9", "cart_id": "c-otro", "variant_id": "v1", "quantity": 1, "created_at": "1"}
        ]
        assert client.delete("/api/cart/items/ci9").status_code == 404


class TestPedidosHTTP:
    def test_crear_pedido_201(self, client, db):
        db.rpc_handlers["place_order"] = lambda params: [{"order_id": "o1"}]

        response = client.post("/api/orders", json={"shipping_address": DIRECCION})
        assert response.status_code == 201

        body = response.json()
        assert body["id"] == "o1"
        assert body["status"] == "pending"
        assert body["items"][0]["product_name"] == "Camisa Oxford Azul"

    def test_carrito_vacio_es_409_invalid_operation(self, client, db):
        def handler(params):
            raise Exception("P0001: CARRITO_VACIO")

        db.rpc_handlers["place_order"] = handler
        response = client.post("/api/orders", json={"shipping_address": DIRECCION})

        assert response.status_code == 409
        assert response.json()["code"] == "invalid_operation"

    def test_stock_insuficiente_es_409(self, client, db):
        def handler(params):
            raise Exception("P0001: STOCK_INSUFICIENTE: Franela Negra")

        db.rpc_handlers["place_order"] = handler
        response = client.post("/api/orders", json={"shipping_address": DIRECCION})

        assert response.status_code == 409
        assert response.json()["code"] == "insufficient_stock"

    def test_direccion_incompleta_es_422(self, client):
        response = client.post(
            "/api/orders",
            json={"shipping_address": {"full_name": "Ana"}},
        )
        assert response.status_code == 422

    def test_pais_debe_tener_dos_letras(self, client):
        invalida = {**DIRECCION, "country": "VENEZUELA"}
        response = client.post("/api/orders", json={"shipping_address": invalida})
        assert response.status_code == 422

    def test_historial_solo_muestra_mis_pedidos(self, client):
        body = client.get("/api/orders").json()
        assert [o["id"] for o in body["items"]] == ["o1"]
        assert body["total"] == 1

    def test_pedido_ajeno_es_404(self, client):
        assert client.get("/api/orders/o2").status_code == 404

    def test_cancelar_pedido(self, client, db):
        capturado = {}

        def handler(params):
            capturado.update(params)
            return None

        db.rpc_handlers["cancel_order"] = handler
        response = client.post("/api/orders/o1/cancel")

        assert response.status_code == 200
        assert capturado == {"p_user_id": "u1", "p_order_id": "o1"}

    def test_cancelar_pedido_ya_enviado_es_409(self, client, db):
        def handler(params):
            raise Exception("P0001: ORDEN_NO_CANCELABLE")

        db.rpc_handlers["cancel_order"] = handler
        response = client.post("/api/orders/o1/cancel")

        assert response.status_code == 409
        assert response.json()["code"] == "invalid_operation"

    def test_sin_sesion_no_se_puede_crear_pedido(self, anon_client):
        response = anon_client.post("/api/orders", json={"shipping_address": DIRECCION})
        assert response.status_code == 401
