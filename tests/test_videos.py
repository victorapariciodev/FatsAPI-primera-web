"""Tests de los videos de la landing.

La lista blanca de URLs se prueba con casos hostiles a proposito: aqui es
donde un descuido se convierte en XSS o en un iframe de phishing.
"""

from __future__ import annotations

import pytest

from fastapi_2026.core.config import settings
from fastapi_2026.core.exceptions import ConflictError, NotFoundError, ValidationError
from fastapi_2026.services.video import VideoService, resolver_video

HOST = settings.supabase_url.split("//")[1].split("/")[0]
ARCHIVO = f"https://{HOST}/storage/v1/object/public/videos/taller.mp4"


class TestResolutorDeUrls:
    @pytest.mark.parametrize(
        "url, esperado",
        [
            (
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            ),
            ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
        ],
    )
    def test_youtube_se_resuelve_a_nocookie(self, url, esperado):
        resultado = resolver_video(url)

        assert resultado["kind"] == "youtube"
        assert resultado["src"] == esperado
        assert "dQw4w9WgXcQ" in resultado["thumb_url"]

    def test_archivo_de_este_storage_se_devuelve_intacto(self):
        resultado = resolver_video(ARCHIVO)

        assert resultado == {"kind": "file", "src": ARCHIVO, "thumb_url": None}

    def test_video_local_en_static_videos(self):
        resultado = resolver_video("/static/videos/taller.mp4")

        assert resultado == {
            "kind": "file",
            "src": "/static/videos/taller.mp4",
            "thumb_url": None,
        }

    @pytest.mark.parametrize(
        "url",
        [
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",       # no HTTPS
            "https://youtube.com.evil.tld/watch?v=dQw4w9WgXcQ", # dominio parecido
            "https://evil.tld/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=corto",            # ID invalido
            "https://otro-proyecto.supabase.co/storage/v1/object/public/videos/x.mp4",
            f"https://{HOST}/storage/v1/object/sign/videos/x.mp4",  # privado
            "javascript:alert(1)",
            "/static/videos/../secreto.mp4",   # path traversal
            "/static/videos/sub/carpeta.mp4",  # sin subcarpetas
            "/static/videos/archivo.html",     # extension no video
            "/static/videos/x.mp4?evil=1",     # query inyectada
            "",
        ],
    )
    def test_url_hostil_se_rechaza(self, url):
        with pytest.raises(ValidationError):
            resolver_video(url)


class TestVideoService:
    def test_solo_lista_videos_activos(self, db):
        resultado = VideoService(db).list_videos()

        assert resultado["total"] == 2
        assert [v["slug"] for v in resultado["items"]] == ["taller-tailwind", "charla-fastapi-en-capas"]

    def test_filtro_por_categoria(self, db):
        resultado = VideoService(db).list_videos(categoria="charla")

        assert len(resultado["items"]) == 1
        assert resultado["items"][0]["categoria"] == "charla"
        # Las categorias siguen siendo todas: el filtro no se come las opciones.
        assert resultado["categorias"] == ["charla", "taller"]

    def test_admin_ve_tambien_los_inactivos(self, db):
        resultado = VideoService(db).list_videos(include_inactive=True)

        assert resultado["total"] == 3
        assert "demo-inactivo" in {v["slug"] for v in resultado["items"]}

    def test_el_item_trae_la_url_ya_resuelta(self, db):
        item = VideoService(db).list_videos()["items"][0]

        assert item["embed_kind"] == "file"
        assert item["src"] == ARCHIVO

    def test_el_contador_devuelve_el_total_de_la_rpc(self, db):
        assert VideoService(db).registrar_visita() == 42

    def test_el_contador_degrada_si_la_rpc_falla(self, db):
        def romper(params):
            raise RuntimeError("401 Unregistered API key")

        db.rpc_handlers["register_landing_visit"] = romper
        assert VideoService(db).registrar_visita() is None

    def test_crear_valida_antes_de_escribir(self, db):
        with pytest.raises(ValidationError):
            VideoService(db).create_video(
                {"title": "Malicioso", "categoria": "demo", "video_url": "javascript:alert(1)"}
            )

        assert len(db.tables["videos"]) == 3

    def test_crear_video_nuevo(self, db):
        creado = VideoService(db).create_video(
            {
                "title": "Taller de testing",
                "categoria": "taller",
                "video_url": "https://youtu.be/abcdefghijk",
            }
        )

        assert creado["slug"] == "taller-de-testing"
        assert creado["embed_kind"] == "youtube"
        assert len(db.tables["videos"]) == 4

    def test_slug_duplicado_se_rechaza(self, db):
        with pytest.raises(ConflictError):
            VideoService(db).create_video(
                {
                    "slug": "taller-tailwind",
                    "title": "Otro titulo",
                    "categoria": "taller",
                    "video_url": ARCHIVO,
                }
            )

    def test_actualizar_url_invalida_no_escribe(self, db):
        with pytest.raises(ValidationError):
            VideoService(db).update_video("vid1", {"video_url": "https://evil.tld/x.mp4"})

        assert db.tables["videos"][0]["video_url"].startswith("https://www.youtube.com/")

    def test_borrar_video_inexistente(self, db):
        with pytest.raises(NotFoundError):
            VideoService(db).delete_video("no-existe")


class TestEndpoints:
    def test_listado_publico(self, anon_client):
        respuesta = anon_client.get("/api/videos")

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["total"] == 2
        assert cuerpo["categorias"] == ["charla", "taller"]

    def test_filtro_publico_por_categoria(self, anon_client):
        cuerpo = anon_client.get("/api/videos", params={"categoria": "taller"}).json()

        assert len(cuerpo["items"]) == 1
        assert cuerpo["items"][0]["slug"] == "taller-tailwind"

    def test_categorias_publicas(self, anon_client):
        assert anon_client.get("/api/videos/categories").json() == ["charla", "taller"]

    def test_admin_puede_listar_y_crear(self, admin_client):
        assert len(admin_client.get("/api/admin/videos").json()["items"]) == 3

        respuesta = admin_client.post(
            "/api/admin/videos",
            json={
                "title": "Nueva charla",
                "categoria": "charla",
                "video_url": "https://youtu.be/abcdefghijk",
            },
        )
        assert respuesta.status_code == 201
        assert respuesta.json()["slug"] == "nueva-charla"

    def test_usuario_normal_no_puede_tocar_videos(self, client):
        assert client.get("/api/admin/videos").status_code == 403
        assert client.post("/api/admin/videos", json={}).status_code == 403

    def test_anonimo_no_puede_tocar_videos(self, anon_client):
        assert anon_client.get("/api/admin/videos").status_code == 401
