"""Tests de la pagina /videos (Stream HUD).

La pagina es publica, usa el mismo VideoService que la API y degrada a un
estado vacio honesto cuando la base no responde. Aqui se verifica eso y que
el boton de la landing efectivamente apunte a una ruta registrada.
"""

from __future__ import annotations


class TestPaginaVideos:
    def test_anonimo_ve_los_videos(self, anon_client):
        respuesta = anon_client.get("/videos")

        assert respuesta.status_code == 200
        html = respuesta.text
        assert "VIDEOS DE LA COMUNIDAD" in html
        assert "Charla: FastAPI en capas" in html
        assert "Taller: tokens de diseño" in html
        assert "Demo retirada" not in html  # inactivo, solo lo ve el admin

    def test_el_video_de_youtube_abre_el_modal(self, anon_client):
        html = anon_client.get("/videos").text

        assert "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" in html
        assert 'data-video-open="stream-charla-fastapi-en-capas"' in html
        assert "<dialog" in html

    def test_filtro_por_categoria(self, anon_client):
        html = anon_client.get("/videos", params={"categoria": "taller"}).text

        assert "Taller: tokens de diseño" in html
        assert "Charla: FastAPI en capas" not in html

    def test_estado_vacio_cuando_no_hay_videos(self, anon_client, db):
        db.tables["videos"] = []

        html = anon_client.get("/videos").text

        assert "Todavía no hay videos publicados en esta categoría." in html

    def test_base_caida_no_tumba_la_pagina(self, anon_client, db):
        original = db.table

        def tabla_caida(nombre: str):
            raise RuntimeError("401 Unregistered API key")

        db.table = tabla_caida
        respuesta = anon_client.get("/videos")
        db.table = original

        assert respuesta.status_code == 200
        assert "Todavía no hay videos publicados en esta categoría." in respuesta.text

    def test_usuario_logueado_tambien_ve_la_nav(self, client):
        """El layout comun incluye el enlace Inicio/Tienda/Mis pedidos/Videos."""
        html = client.get("/videos").text

        assert 'href="/videos"' in html
        assert 'href="/tienda"' in html
