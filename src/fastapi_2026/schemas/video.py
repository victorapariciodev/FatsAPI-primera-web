"""Schemas de la seccion de videos de la landing.

El navegador NO recibe la URL cruda del registro: recibe ``src`` ya validado
y resuelto por el servicio. Asi la lista blanca de hosts vive una sola vez en
el backend y el template solo pinta lo que el servidor decidio.
"""

from pydantic import BaseModel, ConfigDict, Field


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    description: str | None = None
    categoria: str
    # La URL original y el poster se devuelven para que el panel admin pueda
    # editarlos; el navegador de la landing usa `src`, ya validado.
    video_url: str
    poster_url: str | None = None
    # "youtube" -> iframe; "file" -> <video> de Supabase Storage.
    embed_kind: str
    src: str
    thumb_url: str | None = None
    duration_label: str | None = None
    published_at: str | None = None
    is_active: bool = True


class VideoListOut(BaseModel):
    items: list[VideoOut]
    total: int
    categorias: list[str]


class VisitOut(BaseModel):
    total: int | None = None


class VideoCreate(BaseModel):
    slug: str | None = Field(default=None, max_length=140)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    categoria: str = Field(min_length=2, max_length=60)
    video_url: str = Field(min_length=8, max_length=500)
    poster_url: str | None = Field(default=None, max_length=500)
    duration_label: str | None = Field(default=None, max_length=12)
    is_active: bool = True


class VideoUpdate(BaseModel):
    """PATCH parcial: solo se aplican los campos enviados."""

    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    categoria: str | None = Field(default=None, min_length=2, max_length=60)
    video_url: str | None = Field(default=None, min_length=8, max_length=500)
    poster_url: str | None = Field(default=None, max_length=500)
    duration_label: str | None = Field(default=None, max_length=12)
    is_active: bool | None = None
