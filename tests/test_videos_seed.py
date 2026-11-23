"""El seed de YouTube no puede contener URLs que el backend rechace.

Si alguien edita sql/landing_videos_seed.sql y pega un link raro (Shorts,
HTTP, dominio parecido), este test lo delata antes de que llegue a Supabase.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi_2026.services.video import resolver_video

SEED = Path(__file__).resolve().parents[1] / "sql" / "landing_videos_seed.sql"
URL = re.compile(r"https://[^\s']+")


def test_el_seed_existe():
    assert SEED.exists()


def test_todas_las_urls_del_seed_pasan_el_validador():
    texto = SEED.read_text(encoding="utf-8")
    urls = [u.rstrip(",") for u in URL.findall(texto)]

    assert len(urls) == 6

    for url in urls:
        resuelto = resolver_video(url)
        assert resuelto["kind"] == "youtube", url
        assert "youtube-nocookie.com/embed/" in resuelto["src"], url


def test_los_slugs_son_unicos():
    texto = SEED.read_text(encoding="utf-8")
    # Los slugs llevan guion; las categorias del seed no. Eso basta para
    # distinguirlos sin acoplar el test al orden de las columnas.
    slugs = re.findall(r"'([a-z0-9]+(?:-[a-z0-9]+)+)',", texto)

    assert len(slugs) == 6
    assert len(set(slugs)) == len(slugs)
