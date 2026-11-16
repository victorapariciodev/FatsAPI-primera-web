"""Tests de la logica de catalogo (sin HTTP, sin base de datos real)."""

from __future__ import annotations

import pytest

from fastapi_2026.core.exceptions import NotFoundError
from fastapi_2026.services.product import ProductService


def api(db):
    return ProductService(db)


def ids(result: dict) -> list[str]:
    return sorted(p["id"] for p in result["items"])


class TestListProducts:
    def test_catalogo_publico_excluye_inactivos(self, db):
        assert ids(api(db).list_products()) == ["p1", "p2", "p4"]

    def test_admin_incluye_inactivos(self, db):
        result = api(db).list_products(include_inactive=True)
        assert ids(result) == ["p1", "p2", "p3", "p4"]
        assert result["total"] == 4

    def test_busqueda_por_nombre(self, db):
        assert ids(api(db).list_products(search="oxford")) == ["p1"]

    def test_busqueda_por_sku_de_variante(self, db):
        assert ids(api(db).list_products(search="FRA-NEG")) == ["p2"]

    def test_busqueda_es_case_insensitive(self, db):
        assert ids(api(db).list_products(search="OXFORD")) == ["p1"]

    def test_busqueda_sin_resultados(self, db):
        result = api(db).list_products(search="no-existe-123")
        assert result["items"] == []
        assert result["total"] == 0
        assert result["pages"] == 0

    def test_busqueda_no_devuelve_inactivos(self, db):
        assert ids(api(db).list_products(search="cargo")) == []

    def test_busqueda_admin_si_devuelve_inactivos(self, db):
        assert ids(api(db).list_products(search="cargo", include_inactive=True)) == ["p3"]

    def test_filtro_talla_exige_stock(self, db):
        """Una talla agotada no debe aparecer como filtro comprable."""
        assert ids(api(db).list_products(size="M")) == ["p1"]
        assert ids(api(db).list_products(size="S")) == []

    def test_filtro_solo_disponibles(self, db):
        assert ids(api(db).list_products(in_stock=True)) == ["p1", "p2", "p4"]

    def test_busqueda_y_talla_se_intersectan(self, db):
        assert ids(api(db).list_products(search="oxford", size="M")) == ["p1"]
        assert ids(api(db).list_products(search="franela", size="M")) == []

    def test_filtro_categoria(self, db):
        assert ids(api(db).list_products(category="camisas")) == ["p1"]

    def test_rango_de_precio(self, db):
        assert ids(api(db).list_products(min_price=25, max_price=35)) == ["p1"]

    def test_orden_por_precio_ascendente(self, db):
        items = api(db).list_products(sort="price_asc")["items"]
        assert [p["id"] for p in items] == ["p2", "p1", "p4"]

    def test_orden_por_precio_descendente(self, db):
        items = api(db).list_products(sort="price_desc")["items"]
        assert [p["id"] for p in items] == ["p4", "p1", "p2"]

    def test_orden_desconocido_cae_en_newest(self, db):
        items = api(db).list_products(sort="basura")["items"]
        assert [p["id"] for p in items] == ["p4", "p2", "p1"]

    def test_paginacion_cuenta_el_total_real(self, db):
        result = api(db).list_products(page=1, page_size=2)
        assert len(result["items"]) == 2
        assert result["total"] == 3
        assert result["pages"] == 2

        page2 = api(db).list_products(page=2, page_size=2)
        assert len(page2["items"]) == 1

    def test_variantes_vienen_ordenadas_por_talla(self, db):
        product = api(db).get_product("p1")
        assert "product_variants" not in product
        # _SIZE_ORDER pone S antes que M: el orden es de prenda, no alfabetico.
        assert [v["size"] for v in product["variants"]] == ["S", "M"]


class TestGetProduct:
    def test_por_id(self, db):
        assert api(db).get_product("p1")["name"] == "Camisa Oxford Azul"

    def test_producto_inactivo_no_visible(self, db):
        with pytest.raises(NotFoundError):
            api(db).get_product("p3")

    def test_por_slug(self, db):
        assert api(db).get_product_by_slug("franela-negra")["id"] == "p2"

    def test_slug_inexistente(self, db):
        with pytest.raises(NotFoundError):
            api(db).get_product_by_slug("no-existe")


class TestListCategories:
    def test_solo_categorias_activas_y_unicas(self, db):
        categorias = api(db).list_categories()
        assert "pantalones" not in categorias
        assert categorias == sorted(set(categorias))


class TestListSizes:
    def test_solo_tallas_con_stock_de_productos_activos(self, db):
        """S esta agotada y 32 pertenece a un producto inactivo: fuera."""
        assert api(db).list_sizes() == ["M", "L", "XL"]

    def test_orden_de_prenda_no_alfabetico(self, db):
        db.tables["product_variants"].append(
            {
                "id": "v9",
                "product_id": "p2",
                "size": "XS",
                "color": "negro",
                "sku": "FRA-NEG-XS",
                "stock": 2,
                "created_at": "9",
            }
        )
        assert api(db).list_sizes()[0] == "XS"


class TestCountInactive:
    def test_cuenta_los_desactivados(self, db):
        assert api(db).count_inactive() == 1

    def test_reactivar_baja_el_contador(self, db):
        api(db).update_product("p3", {"is_active": True})
        assert api(db).count_inactive() == 0
