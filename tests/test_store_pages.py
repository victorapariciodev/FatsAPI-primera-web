"""Tests de las paginas HTML y del contrato UI <-> API <-> base de datos.

Dos objetivos concretos:
  1. Romper el build si una pagina deja de renderizar con datos reales
     (Jinja falla en silencio hasta que alguien la abre en el navegador).
  2. Garantizar que cada endpoint que el front invoca EXISTE, que cada link
     interno apunta a una ruta registrada y que ningun concepto de pago se
     colo en el diseno. Un boton que llama a una ruta fantasma es un boton
     muerto, y este proyecto no acepta botones muertos.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fastapi_2026.main import app

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATES = RAIZ / "src" / "fastapi_2026" / "templates" / "store"
STORE_JS = RAIZ / "src" / "fastapi_2026" / "static" / "js" / "store.js"

PARAM_LITERAL = re.compile(r"\$\{[^}]+\}|\{\{[^}]+\}\}")
API_LITERAL = re.compile(r"/api/[A-Za-z0-9_/${}.\-]*")
HREF_LITERAL = re.compile(r'(?:href|action)="(/[^"]*)"')


# ----------------------------------------------------------------------
# Utilidades del test de contrato (no son fixtures)
# ----------------------------------------------------------------------
def _segmentos(url: str) -> tuple[str, ...]:
    """Normaliza una URL a segmentos, con los parametros como '{p}'."""
    url = url.split("?", 1)[0].split("#", 1)[0]
    url = PARAM_LITERAL.sub("{p}", url).strip()
    return tuple(segmento for segmento in url.split("/") if segmento)


def _coincide(literal: tuple[str, ...], plantilla: tuple[str, ...]) -> bool:
    """Compara segmento a segmento; '{...}' y '{p}' son comodines."""
    if len(literal) != len(plantilla):
        return False

    for valor, esperado in zip(literal, plantilla):
        comodin = valor == "{p}" or (esperado.startswith("{") and esperado.endswith("}"))
        if not comodin and valor != esperado:
            return False
    return True


def _rutas_registradas() -> list[tuple[str, ...]]:
    """Universo de rutas reales.

    Se usa el OpenAPI y no ``app.routes``: las versiones nuevas de FastAPI
    envuelven los routers incluidos en ``_IncludedRouter``, asi que
    ``app.routes`` ya no expone los paths individuales. El esquema OpenAPI es
    justamente el contrato publicado, que es lo que queremos verificar.
    """
    return [_segmentos(ruta) for ruta in app.openapi()["paths"]]


class TestCatalogoPagina:
    def test_renderiza_200_con_productos_activos(self, client):
        respuesta = client.get("/tienda")
        assert respuesta.status_code == 200

        html = respuesta.text
        assert "CATÁLOGO" in html
        assert "Camisa Oxford Azul" in html
        assert "Franela Negra" in html
        # p3 esta inactivo: no debe asomar en el catalogo publico.
        assert "Pantalon Cargo" not in html

    def test_campos_de_precio_vacios_no_rompen_el_filtro(self, client):
        respuesta = client.get(
            "/tienda",
            params={
                "min_price": "",
                "max_price": "",
                "sort": "price_asc",
                "in_stock": "true",
            },
        )

        assert respuesta.status_code == 200
        assert "Camisa Oxford Azul" in respuesta.text

    def test_precio_no_numerico_sigue_devolviendo_422(self, client):
        respuesta = client.get("/tienda", params={"min_price": "no-es-precio"})

        assert respuesta.status_code == 422

    def test_muestra_y_sirve_imagenes_locales_de_productos(self, client, db):
        db.tables["products"][0]["image_url"] = "/static/img/jeans-indigo.jpg"

        html = client.get("/tienda").text
        assert 'src="/static/img/jeans-indigo.jpg"' in html

        imagen = client.get("/static/img/jeans-indigo.jpg")
        assert imagen.status_code == 200
        assert imagen.headers["content-type"] == "image/jpeg"
        assert imagen.content

    def test_la_tarjeta_no_promete_agregar_sin_talla(self, client):
        """La tarjeta no conoce variant_id: su CTA lleva al detalle."""
        html = client.get("/tienda").text
        assert "Elegir talla" in html
        assert "Agregar al carrito" not in html

    def test_tallas_solo_muestran_las_comprables(self, client):
        """La talla S de la camisa esta agotada: no puede ser filtro."""
        html = client.get("/tienda").text

        # Solo las chips del panel de filtros (w-9 h-9). Las de la tarjeta
        # muestran todo el catalogo de tallas, tachando las agotadas.
        filtros = re.findall(r'class="w-9 h-9[^"]*">\s*([A-Z]+)\s*<', html)

        assert "M" in filtros
        assert "S" not in filtros

    def test_la_tarjeta_tacha_la_talla_agotada(self, client):
        html = client.get("/tienda").text
        assert "line-through" in html

    def test_busqueda_por_sku(self, client):
        html = client.get("/tienda", params={"q": "FRA-NEG"}).text
        assert "Franela Negra" in html
        assert "Camisa Oxford Azul" not in html

    def test_filtro_talla_agotada_devuelve_estado_vacio(self, client):
        html = client.get("/tienda", params={"size": "S"}).text
        assert "No encontramos prendas con esos filtros" in html

    def test_orden_invalido_se_coacciona_en_vez_de_reventar(self, client):
        respuesta = client.get("/tienda", params={"sort": "basura"})
        assert respuesta.status_code == 200
        assert "Camisa Oxford Azul" in respuesta.text

    def test_busqueda_sin_resultados_no_rompe(self, client):
        html = client.get("/tienda", params={"q": "no-existe-123"}).text
        assert "MOSTRANDO 0 DE 0" in html

    def test_anonimo_puede_ver_el_catalogo(self, anon_client):
        html = anon_client.get("/tienda").text
        assert "CATÁLOGO" in html
        assert "Entrar" in html

    def test_admin_ve_el_enlace_de_gestion(self, admin_client):
        assert 'href="/admin/productos"' in admin_client.get("/tienda").text

    def test_usuario_normal_no_ve_el_enlace_de_gestion(self, client):
        assert 'href="/admin/productos"' not in client.get("/tienda").text


class TestDetallePagina:
    def test_renderiza_con_variantes_reales(self, client):
        respuesta = client.get("/tienda/camisa-oxford-azul")
        assert respuesta.status_code == 200

        html = respuesta.text
        assert "Camisa Oxford Azul" in html
        assert 'data-variant-id="v1"' in html
        assert "Agregar al carrito" in html

    def test_preselecciona_la_primera_variante_con_stock(self, client):
        """S esta agotada; la seleccion inicial debe ser M y su SKU."""
        html = client.get("/tienda/camisa-oxford-azul").text
        assert "SKU: CAM-OXF-AZ-M" in html
        assert "DISPONIBLES: 8 UNIDADES" in html

    def test_marca_la_talla_agotada(self, client):
        html = client.get("/tienda/camisa-oxford-azul").text
        assert "agotado" in html

    def test_preselecciona_la_talla_pedida_por_la_tarjeta(self, client, db):
        """El chip ?size= de la tarjeta debe llegar al detalle y servir."""
        db.tables["product_variants"].append(
            {
                "id": "v9",
                "product_id": "p1",
                "size": "L",
                "color": "azul",
                "sku": "CAM-OXF-AZ-L",
                "stock": 4,
                "created_at": "9",
            }
        )
        html = client.get("/tienda/camisa-oxford-azul", params={"size": "L"}).text

        assert "SKU: CAM-OXF-AZ-L" in html
        assert "DISPONIBLES: 4 UNIDADES" in html
        assert 'data-variant-id="v9"' in html
        assert 'data-selected="true"' in html

    def test_no_preselecciona_una_talla_agotada(self, client):
        """?size=S (agotada) cae en la primera comprable en vez de mentir."""
        html = client.get("/tienda/camisa-oxford-azul", params={"size": "S"}).text
        assert "SKU: CAM-OXF-AZ-M" in html

    def test_slug_inexistente_vuelve_al_catalogo(self, client):
        respuesta = client.get("/tienda/no-existe", follow_redirects=False)
        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/tienda"

    def test_producto_inactivo_no_es_accesible(self, client):
        respuesta = client.get("/tienda/pantalon-cargo", follow_redirects=False)
        assert respuesta.status_code == 303

    def test_anonimo_ve_el_aviso_de_sesion(self, anon_client):
        assert "Inicia sesión para continuar" in anon_client.get(
            "/tienda/camisa-oxford-azul"
        ).text


class TestCarritoPagina:
    def _con_items(self, db):
        db.tables["cart_items"] = [
            {
                "id": "ci1",
                "cart_id": "c1",
                "variant_id": "v1",
                "quantity": 1,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]

    def test_carrito_vacio_invita_al_catalogo(self, client):
        html = client.get("/carrito").text
        assert "Tu carrito está vacío" in html
        assert "Vaciar carrito" not in html

    def test_totales_los_calcula_el_servidor(self, client, db):
        self._con_items(db)
        html = client.get("/carrito").text

        assert "$29.90" in html  # subtotal
        assert "$34.90" in html  # total con envio
        assert "Vaciar carrito" in html
        assert "No se procesa pago en línea." in html

    def test_el_nombre_enlaza_al_slug_no_al_id(self, client, db):
        """Regresion: el detalle es /tienda/{slug} y el carrito traia el id."""
        self._con_items(db)
        html = client.get("/carrito").text
        assert 'href="/tienda/camisa-oxford-azul"' in html
        assert 'href="/tienda/p1"' not in html

    def test_envio_gratis_sobre_el_umbral(self, client, db):
        db.tables["cart_items"] = [
            {
                "id": "ci1",
                "cart_id": "c1",
                "variant_id": "v5",  # 60.00
                "quantity": 1,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        html = client.get("/carrito").text
        assert "GRATIS" in html
        assert "$60.00" in html

    def test_anonimo_va_al_login(self, anon_client):
        respuesta = anon_client.get("/carrito", follow_redirects=False)
        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/login"


class TestConfirmarPagina:
    def test_formulario_tiene_exactamente_los_campos_del_schema(self, client, db):
        db.tables["cart_items"] = [
            {
                "id": "ci1",
                "cart_id": "c1",
                "variant_id": "v1",
                "quantity": 1,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        html = client.get("/pedido/confirmar").text

        for campo in (
            "full_name",
            "phone",
            "address_line",
            "city",
            "state",
            "postal_code",
            "country",
        ):
            assert f'name="{campo}"' in html, campo

        assert "NO SE PROCESA PAGO EN LÍNEA" in html

    def test_sin_tarjeta_ni_pasarela_en_el_formulario(self, client, db):
        db.tables["cart_items"] = [
            {
                "id": "ci1",
                "cart_id": "c1",
                "variant_id": "v1",
                "quantity": 1,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
        html = client.get("/pedido/confirmar").text.lower()
        for prohibido in ("card_number", "cvv", "stripe", "paypal", "tarjeta"):
            assert prohibido not in html, prohibido

    def test_carrito_vacio_redirige_al_carrito(self, client):
        respuesta = client.get("/pedido/confirmar", follow_redirects=False)
        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/carrito"

    def test_anonimo_va_al_login(self, anon_client):
        respuesta = anon_client.get("/pedido/confirmar", follow_redirects=False)
        assert respuesta.headers["location"] == "/login"


class TestPedidosPagina:
    def test_historial_muestra_el_pedido_real(self, client):
        html = client.get("/pedidos").text

        assert "MIS PEDIDOS" in html
        assert "NK-o1" in html
        assert "Camisa Oxford Azul" in html
        assert "Cancelar pedido" in html

    def test_aviso_de_pedido_creado(self, client):
        html = client.get("/pedidos", params={"creado": 1}).text
        assert "Pedido registrado" in html

    def test_sin_pedidos_muestra_estado_vacio(self, client, db):
        db.tables["orders"] = [o for o in db.tables["orders"] if o["user_id"] != "u1"]
        html = client.get("/pedidos").text
        assert "Todavía no tienes pedidos" in html

    def test_pedido_cancelado_no_ofrece_cancelar(self, client, db):
        db.tables["orders"][0]["status"] = "cancelled"
        html = client.get("/pedidos").text
        assert "cancelled" in html
        assert "Cancelar pedido" not in html

    def test_busqueda_de_pedidos_no_existe_en_el_diseno(self, client):
        """El contrato dice: historial sin buscador propio.

        El buscador del header es del catalogo (action=/tienda) y es global.
        Lo que no debe existir es un formulario que filtre pedidos, porque
        no hay endpoint que lo respalde.
        """
        html = client.get("/pedidos").text
        assert 'action="/pedidos"' not in html
        assert 'action="/tienda"' in html  # el del header sigue siendo real

    def test_anonimo_va_al_login(self, anon_client):
        respuesta = anon_client.get("/pedidos", follow_redirects=False)
        assert respuesta.headers["location"] == "/login"


class TestAdminPagina:
    def test_admin_ve_el_panel(self, admin_client):
        html = admin_client.get("/admin/productos").text
        assert "GESTIÓN DE PRODUCTOS" in html
        assert "Camisa Oxford Azul" in html
        assert "1 INACTIVOS" in html

    def test_por_defecto_esconde_inactivos(self, admin_client):
        assert "Pantalon Cargo" not in admin_client.get("/admin/productos").text

    def test_checkbox_trae_los_inactivos(self, admin_client):
        html = admin_client.get(
            "/admin/productos", params={"include_inactive": "true"}
        ).text
        assert "Pantalon Cargo" in html

    def test_muestra_las_variantes_para_reponer_stock(self, admin_client):
        html = admin_client.get("/admin/productos").text
        assert 'data-variant="v1"' in html
        assert "CAM-OXF-AZ-M" in html

    def test_usuario_normal_recibe_403(self, client):
        assert client.get("/admin/productos").status_code == 403

    def test_anonimo_va_al_login(self, anon_client):
        respuesta = anon_client.get("/admin/productos", follow_redirects=False)
        assert respuesta.headers["location"] == "/login"


class TestContratoUI:
    """El contrato que el diseno firmo con la base de datos."""

    def _fuentes(self) -> dict[str, str]:
        fuentes = {
            ruta.name: ruta.read_text(encoding="utf-8")
            for ruta in TEMPLATES.glob("*.html")
        }
        fuentes["store.js"] = STORE_JS.read_text(encoding="utf-8")
        return fuentes

    def test_todo_endpoint_invocado_por_el_front_existe(self):
        rutas = _rutas_registradas()
        invocados: list[str] = []

        for nombre, texto in self._fuentes().items():
            for literal in API_LITERAL.findall(texto):
                literal = literal.rstrip("/")
                if literal == "/api":
                    # Prefijo suelto en un comentario ("contra /api/*"), no
                    # una llamada real.
                    continue
                invocados.append(literal)

        assert invocados, "el front no invoca ningun endpoint: algo se rompio"

        huerfanos = sorted(
            {
                literal
                for literal in invocados
                if not any(_coincide(_segmentos(literal), ruta) for ruta in rutas)
            }
        )
        assert huerfanos == [], f"endpoints inexistentes en el front: {huerfanos}"

    def test_todo_link_interno_apunta_a_una_ruta_registrada(self):
        rutas = _rutas_registradas()
        muertos: set[str] = set()

        for nombre, texto in self._fuentes().items():
            if not nombre.endswith(".html"):
                continue
            for destino in HREF_LITERAL.findall(texto):
                if not any(_coincide(_segmentos(destino), ruta) for ruta in rutas):
                    muertos.add(destino)

        assert muertos == set(), f"links sin ruta: {sorted(muertos)}"

    def test_no_hay_conceptos_de_pago_en_el_diseno(self):
        prohibidos = (
            r"\bstripe\b",
            r"\bpaypal\b",
            r"\bvisa\b",
            r"\bmastercard\b",
            r"\bamex\b",
            r"\bcvv\b",
            r"card_number",
            r"\btarjeta\b",
            r"/paid\b",
        )
        for nombre, texto in self._fuentes().items():
            for patron in prohibidos:
                assert not re.search(patron, texto, re.IGNORECASE), (
                    f"{nombre} menciona un concepto de pago: {patron}"
                )

    def test_las_paginas_usan_el_css_compilado(self):
        """Nada de CDN de Tailwind: el diseno corre sobre app.css real."""
        for nombre, texto in self._fuentes().items():
            assert "cdn.tailwindcss.com" not in texto, nombre
            assert "tailwind.config" not in texto, nombre

    def test_el_layout_no_duplica_endpoints_en_js(self):
        """La capa fetch vive en store.js; las plantillas solo la consumen."""
        for ruta in TEMPLATES.glob("*.html"):
            texto = ruta.read_text(encoding="utf-8")
            assert "fetch(" not in texto, f"{ruta.name} llama fetch directamente"
