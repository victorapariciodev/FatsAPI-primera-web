"""Endpoints de la seccion de videos de la landing.

Rutas publicas de lectura y rutas de administracion protegidas por rol.
El contador de visitas NO es un endpoint: se registra como efecto de GET /,
que es el unico momento en que alguien visita realmente la landing.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from supabase import Client

from fastapi_2026.api.db import get_db
from fastapi_2026.api.deps import require_admin
from fastapi_2026.schemas.video import VideoCreate, VideoListOut, VideoOut, VideoUpdate
from fastapi_2026.services.video import VideoService

router = APIRouter(prefix="/api/videos", tags=["Videos"])


@router.get("", response_model=VideoListOut, summary="Videos publicos de la landing")
def list_videos(
    categoria: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=24, ge=1, le=60),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    return VideoService(db).list_videos(categoria=categoria, limit=limit)


@router.get("/categories", response_model=list[str], summary="Categorias de videos")
def list_categories(db: Client = Depends(get_db)) -> list[str]:
    return VideoService(db).list_categories()


# ---------------------------------------------------------------------
# Administracion: misma validacion de rol que /api/admin/products.
# ---------------------------------------------------------------------
admin_router = APIRouter(prefix="/api/admin", tags=["Admin"])


@admin_router.get(
    "/videos", response_model=VideoListOut, summary="Listar videos (admin)"
)
def list_all_videos(
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    return VideoService(db).list_videos(include_inactive=True, limit=60)


@admin_router.post(
    "/videos",
    response_model=VideoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear video (admin)",
)
def create_video(
    payload: VideoCreate,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    return VideoService(db).create_video(payload.model_dump(exclude_unset=True))


@admin_router.patch(
    "/videos/{video_id}",
    response_model=VideoOut,
    summary="Actualizar video (admin)",
)
def update_video(
    video_id: str,
    payload: VideoUpdate,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    return VideoService(db).update_video(video_id, payload.model_dump(exclude_unset=True))


@admin_router.delete(
    "/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar video (admin)",
)
def delete_video(
    video_id: str,
    db: Client = Depends(get_db),
    _: dict = Depends(require_admin),
) -> Response:
    VideoService(db).delete_video(video_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
