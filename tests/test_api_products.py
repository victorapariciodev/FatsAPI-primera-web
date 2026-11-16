"""Tests de la capa HTTP de catalogo: contrato, permisos y errores."""

from __future__ import annotations

from decimal import Decimal


class TestCatalogoPublico:
    def test_listado_200_y_solo_activos(self, client):
        response = client.get("/api/products")
        assert response.status_code == 200

        body = response.json()
        assert sorted(p["id"] for p in body["items"]) == ["p1", "p2", "p4"]
        assert body["total"] == 3

    def test_busqueda_por_sku_llega_al_servicio(self, client):
        body = client.get("/api/products", params={"search": "CAM-OXF"}).json()
        assert [p["id"] for p in body["items"]] == ["p1"]

    def test_filtro_talla_sin_stock_no_devuelve_nada(self, client):
        body = client.get("/api/products", params={"size": "S"}).json()
        assert body["items"] == []

    def test_orden_precio_ascendente(self, client):
        body = client.get("/api/products", params={"sort": "price_asc"}).json()
        assert [p["id"] for p in body["items"]] == ["p2", "p1", "p4"]

    def test_sort_invalido_es_422(self, client):
        assert client.get("/api/products", params={"sort": "basura"}).status_code == 422

    def test_page_size_fuera_de_rango_es_422(self, client):
        assert client.get("/api/products", params={"page_size": 500}).status_code == 422

    def test_precio_serializado_como_string(self, client):
        """Decimal viaja como string: el front formatea, no hace aritmetica float."""
        body = client.get("/api/products", params={"category": "camisas"}).json()
        precio = body["items"][0]["price"]

        assert isinstance(precio, str)
        assert Decimal(precio) == Decimal("29.90")

    def test_detalle_por_slug(self, client):
        assert client.get("/api/products/by-slug/franela-negra").json()["id"] == "p2"

    def test_slug_inexistente_404_con_codigo(self, client):
        response = client.get("/api/products/by-slug/no-existe")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    def test_categorias(self, client):
        body = client.get("/api/products/categories").json()
        assert "camisas" in body
        assert "pantalones" not in body  # solo existe en un producto inactivo


class TestAdmin:
    def test_listar_incluyendo_inactivos(self, admin_client):
        body = admin_client.get("/api/admin/products").json()
        assert sorted(p["id"] for p in body["items"]) == ["p1", "p2", "p3", "p4"]

    def test_usuario_normal_no_puede_listar_admin(self, client):
        assert client.get("/api/admin/products").status_code == 403

    def test_usuario_normal_no_puede_crear_producto(self, client):
        response = client.post(
            "/api/products",
            json={
                "name": "Producto pirata",
                "category": "camisas",
                "price": 10,
                "variants": [{"size": "M", "color": "azul", "sku": "PIR-1", "stock": 1}],
            },
        )
        assert response.status_code == 403

    def test_crear_producto_sin_variantes_es_422(self, admin_client):
        response = admin_client.post(
            "/api/products",
            json={
                "name": "Sin variantes",
                "category": "camisas",
                "price": 10,
                "variants": [],
            },
        )
        assert response.status_code == 422

    def test_crear_producto_precio_cero_es_422(self, admin_client):
        response = admin_client.post(
            "/api/products",
            json={
                "name": "Precio cero",
                "category": "camisas",
                "price": 0,
                "variants": [{"size": "M", "color": "azul", "sku": "PC-1", "stock": 1}],
            },
        )
        assert response.status_code == 422

    def test_crear_producto_genera_slug(self, admin_client):
        response = admin_client.post(
            "/api/products",
            json={
                "name": "Gorra Cyber",
                "category": "accesorios",
                "price": 12.5,
                "variants": [{"size": "U", "color": "negro", "sku": "GOR-CYB-U", "stock": 4}],
            },
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "gorra-cyber"

    def test_reponer_stock(self, admin_client):
        response = admin_client.patch(
            "/api/products/p1/variants/v1/stock", json={"stock": 20}
        )
        assert response.status_code == 200
        assert response.json()["stock"] == 20

    def test_stock_negativo_es_422(self, admin_client):
        response = admin_client.patch(
            "/api/products/p1/variants/v1/stock", json={"stock": -1}
        )
        assert response.status_code == 422

    def test_desactivar_producto_es_borrado_logico(self, admin_client, db):
        response = admin_client.delete("/api/products/p1")
        assert response.status_code == 204

        producto = next(p for p in db.tables["products"] if p["id"] == "p1")
        assert producto["is_active"] is False
        assert any(p["id"] == "p1" for p in db.tables["products"])  # no se borra la fila
