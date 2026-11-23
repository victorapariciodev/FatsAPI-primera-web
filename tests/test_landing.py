"""Tests de la landing publica y de su contrato con el diseno.

La landing dejo de ser un HTML estatico: aqui se verifica que cada numero que
muestra venga de un servicio, que la seccion de videos renderice URLs ya
validadas, y que no haya links muertos ni CDN de Tailwind colado.
"""

from __future__ import annotations

from pathlib import Path

from fastapi_2026.core.config import settings

from .test_store_pages import HREF_LITERAL, _coincide, _rutas_registradas, _segmentos

RAIZ = Path(__file__).resolve().parents[1]
LANDING = RAIZ / "src" / "fastapi_2026" / "templates" / "landing.html"
LANDING_JS = RAIZ / "src" / "fastapi_2026" / "static" / "js" / "landing.js"
HOST = settings.supabase_url.split("//")[1].split("/")[0]


class TestLandingConDatos:
    def test_anonimo_ve_la_portada_con_videos(self, anon_client):
        respuesta = anon_client.get("/")

        assert respuesta.status_code == 200
        html = respuesta.text
        assert "VIDEOS DE LA COMUNIDAD" in html
        assert "Charla: FastAPI en capas" in html
        assert "Taller: tokens de diseño" in html
        # El inactivo no se cuela en la lista publica.
        assert "Demo retirada" not in html

    def test_el_video_de_youtube_lleva_su_miniatura_y_el_modal(self, anon_client):
        html = anon_client.get("/").text

        assert "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg" in html
        assert "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" in html
        assert 'data-video-open="video-charla-fastapi-en-capas"' in html
        assert "<dialog" in html

    def test_el_video_de_storage_usa_etiqueta_video(self, anon_client):
        html = anon_client.get("/").text

        assert f"https://{HOST}/storage/v1/object/public/videos/taller.mp4" in html
        assert "<video " in html

    def test_filtro_por_categoria(self, anon_client):
        html = anon_client.get("/", params={"categoria": "taller"}).text

        assert "Taller: tokens de diseño" in html
        assert "Charla: FastAPI en capas" not in html

    def test_estado_vacio_cuando_no_hay_videos(self, anon_client, db):
        db.tables["videos"] = []

        html = anon_client.get("/").text

        assert "Todavía no hay videos publicados en esta categoría." in html

    def test_las_metricas_son_reales(self, anon_client):
        html = anon_client.get("/").text

        assert "// CATÁLOGO ACTIVO" in html
        assert "// VISITAS" in html
        assert ">42<" in html          # total que devuelve la RPC del fake
        assert "STATUS: ONLINE" in html
        assert "0ms" not in html
        assert "STATUS: STANDBY" not in html

    def test_sin_base_la_portada_degrada_pero_no_miente(self, anon_client, db):
        original = db.table

        def tabla_caida(nombre: str):
            raise RuntimeError("401 Unregistered API key")

        db.table = tabla_caida

        respuesta = anon_client.get("/")
        assert respuesta.status_code == 200
        assert "STATUS: SIN DATOS" in respuesta.text
        assert respuesta.text.count("N/D") >= 1
        db.table = original


class TestContratoLanding:
    def test_usa_el_css_compilado_no_el_cdn(self):
        html = LANDING.read_text(encoding="utf-8")

        assert "cdn.tailwindcss.com" not in html
        assert "tailwind.config" not in html
        assert "/css/app.css" in html
        assert 'data-shell="community"' in html

    def test_no_hay_fetch_suelto(self):
        assert "fetch(" not in LANDING.read_text(encoding="utf-8")
        assert "fetch(" not in LANDING_JS.read_text(encoding="utf-8")

    def test_todo_link_interno_apunta_a_una_ruta_registrada(self):
        rutas = _rutas_registradas()
        html = LANDING.read_text(encoding="utf-8")

        muertos = {
            destino
            for destino in HREF_LITERAL.findall(html)
            if not any(_coincide(_segmentos(destino), ruta) for ruta in rutas)
        }

        assert muertos == set(), f"links sin ruta: {sorted(muertos)}"

    def test_el_nav_stream_hud_apunta_a_la_seccion_real(self):
        html = LANDING.read_text(encoding="utf-8")

        assert 'href="#videos"' in html
        assert 'id="videos"' in html


class TestPanelAdminDeVideos:
    def test_admin_ve_el_panel(self, admin_client):
        respuesta = admin_client.get("/admin/videos")

        assert respuesta.status_code == 200
        assert "GESTIÓN DE VIDEOS" in respuesta.text
        assert "Demo retirada" in respuesta.text  # el admin ve tambien los inactivos

    def test_usuario_normal_recibe_403(self, client):
        assert client.get("/admin/videos").status_code == 403

    def test_anonimo_va_al_login(self, anon_client):
        respuesta = anon_client.get("/admin/videos", follow_redirects=False)

        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/login"
