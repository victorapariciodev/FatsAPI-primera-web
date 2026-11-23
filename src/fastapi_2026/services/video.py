"""Logica de los videos de la landing y del contador de visitas.

Regla de seguridad que manda en este archivo: la URL que llega del admin se
valida contra una lista blanca de hosts AQUI, antes de tocar el navegador.
Un ``<iframe src="{{ video_url }}">`` sin filtrar es una invitacion a inyectar
cualquier pagina (y a convertir la landing en un phishing). Jinja autoescapa
atributos, pero el autoescape no decide si el host es de confianza: eso es
trabajo del dominio.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qs, urlparse

from supabase import Client

from fastapi_2026.core.config import settings
from fastapi_2026.core.exceptions import ConflictError, NotFoundError, ValidationError

TABLA = "videos"
LIMITE_PUBLICO = 24

_ID_YOUTUBE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOSTS_YOUTUBE = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
PREFIJO_STORAGE = "/storage/v1/object/public/"


def _slugify(value: str) -> str:
    normalizado = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalizado.lower()).strip("-") or "video"


def resolver_video(url: str) -> dict[str, str | None]:
    """Traduce una URL permitida a ``(kind, src, thumb_url)``.

    Solo dos formatos:
      * YouTube (watch / youtu.be / embed) -> iframe de youtube-nocookie;
      * archivo publico de ESTE proyecto de Supabase Storage -> <video>.

    Todo lo demas se rechaza con ValidationError (422). No se acepta HTTP,
    ni dominios parecidos (`youtube.com.evil.tld`), ni rutas de storage de
    otro proyecto.
    """
    valor = (url or "").strip()
    try:
        parsed = urlparse(valor)
    except Exception as exc:  # noqa: BLE001 - una URL rota es entrada invalida
        raise ValidationError("La URL del video no es valida.") from exc

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValidationError("La URL del video debe ser HTTPS.")

    host = parsed.hostname.lower()
    host_storage = urlparse(settings.supabase_url).hostname or ""

    if host in _HOSTS_YOUTUBE:
        if host.endswith("youtu.be"):
            video_id = parsed.path.strip("/").split("/")[0]
        elif parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith("/embed/"):
            video_id = parsed.path.split("/")[2]
        else:
            raise ValidationError("Formato de YouTube no reconocido.")

        if not _ID_YOUTUBE.fullmatch(video_id):
            raise ValidationError("El ID del video de YouTube no es valido.")

        return {
            "kind": "youtube",
            # nocookie: no instala cookies de seguimiento antes de dar play.
            "src": f"https://www.youtube-nocookie.com/embed/{video_id}",
            "thumb_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        }

    if host == host_storage and parsed.path.startswith(PREFIJO_STORAGE):
        return {"kind": "file", "src": valor, "thumb_url": None}

    raise ValidationError(
        "Solo se admiten videos de YouTube o archivos publicos de este "
        "proyecto de Supabase Storage."
    )


class VideoService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Lecturas publicas
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize(row: dict[str, Any]) -> dict[str, Any]:
        datos = dict(row)
        resuelto = resolver_video(datos["video_url"])
        datos["embed_kind"] = resuelto["kind"]
        datos["src"] = resuelto["src"]
        # En YouTube la miniatura la genera el ID; en Storage usa el poster
        # que cargo el admin.
        datos["thumb_url"] = resuelto["thumb_url"] or datos.get("poster_url")
        return datos

    def list_videos(
        self,
        categoria: str | None = None,
        limit: int = LIMITE_PUBLICO,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        consulta = self.db.table(TABLA).select("*", count="exact")
        if not include_inactive:
            consulta = consulta.eq("is_active", True)
        if categoria and categoria.strip():
            consulta = consulta.eq("categoria", categoria.strip())

        respuesta = consulta.order("published_at", desc=True).limit(limit).execute()
        filas = respuesta.data or []

        return {
            "items": [self._normalize(fila) for fila in filas],
            "total": respuesta.count or 0,
            "categorias": self.list_categories(include_inactive=include_inactive),
        }

    def list_categories(self, include_inactive: bool = False) -> list[str]:
        consulta = self.db.table(TABLA).select("categoria")
        if not include_inactive:
            consulta = consulta.eq("is_active", True)
        filas = consulta.execute().data or []
        return sorted({str(fila["categoria"]) for fila in filas if fila.get("categoria")})

    def registrar_visita(self) -> int | None:
        """Incrementa el contador con la RPC atomica.

        Si la base no responde devuelve None: una landing caida no puede
        convertirse en un 500 por culpa de una metrica decorativa.
        """
        try:
            datos = self.db.rpc("register_landing_visit", {}).execute().data
        except Exception as exc:  # noqa: BLE001 - degrade voluntario
            print(f"⚠️  No se pudo registrar la visita: {exc}")
            return None

        if isinstance(datos, list):
            datos = datos[0] if datos else None
        try:
            return int(datos) if datos is not None else None
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Escrituras (solo admin; el router valida el rol)
    # ------------------------------------------------------------------
    def get_video(self, video_id: str, include_inactive: bool = True) -> dict[str, Any]:
        consulta = self.db.table(TABLA).select("*").eq("id", video_id)
        if not include_inactive:
            consulta = consulta.eq("is_active", True)
        filas = consulta.limit(1).execute().data or []
        if not filas:
            raise NotFoundError("El video no existe.")
        return self._normalize(filas[0])

    def create_video(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        # Validar ANTES de escribir: nunca se guarda una URL que luego no se
        # podra renderizar.
        resolver_video(payload["video_url"])
        payload["slug"] = payload.get("slug") or _slugify(payload["title"])

        try:
            creados = self.db.table(TABLA).insert(payload).execute().data or []
        except Exception as exc:
            if "duplicate key" in str(exc):
                raise ConflictError(f"Ya existe un video con el slug '{payload['slug']}'.") from exc
            raise
        if not creados:
            raise ConflictError("No se pudo crear el video.")
        return self.get_video(creados[0]["id"])

    def update_video(self, video_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self.get_video(video_id)
        if not data:
            raise ConflictError("No enviaste ningun campo para actualizar.")
        if "video_url" in data:
            resolver_video(data["video_url"])

        try:
            actualizados = (
                self.db.table(TABLA).update(data).eq("id", video_id).execute().data or []
            )
        except Exception as exc:
            if "duplicate key" in str(exc):
                raise ConflictError("El slug ya esta en uso por otro video.") from exc
            raise
        if not actualizados:
            raise NotFoundError("El video no existe.")
        return self.get_video(video_id)

    def delete_video(self, video_id: str) -> None:
        self.get_video(video_id)
        self.db.table(TABLA).delete().eq("id", video_id).execute()
