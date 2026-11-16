"""Verifica las llaves de Supabase del .env, una por una.

Nace de un 500 mudo: con la secret key equivocada cada pagina reventaba y el
motivo real ("401 Unregistered API key") quedaba enterrado dentro del error de
PostgREST. Este script no levanta uvicorn ni toca la aplicacion: pregunta
directo al gateway y dice **cual** llave esta mal y que hacer.

No imprime secretos: solo longitud, prefijo y el veredicto.

Uso:
    uv run python scripts/check_keys.py

Codigos de salida:
    0  las dos llaves responden
    1  alguna llave esta mal (se explica cual y por que)
"""

from __future__ import annotations

import base64
import json
import sys
from urllib.parse import urlparse

import httpx

from fastapi_2026.core.config import settings

TIMEOUT = 20.0


def _proyecto(url: str) -> str:
    return urlparse(url).netloc.split(".")[0]


def _claims(llave: str) -> dict | None:
    """Devuelve el payload si la llave es un JWT (formato viejo), si no None."""
    if not llave.startswith("eyJ") or llave.count(".") != 2:
        return None
    payload = llave.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:  # noqa: BLE001 - si no se puede leer, no hay veredicto
        return None


def _motivo(respuesta: httpx.Response) -> str:
    """Traduce la respuesta del gateway a una instruccion concreta."""
    cuerpo = respuesta.text.lower()

    if "unregistered api key" in cuerpo or "invalid api key" in cuerpo:
        return (
            "esa llave NO existe en el proyecto: fue rotada o es de otro "
            "proyecto. Copiala de nuevo desde Project Settings > API Keys."
        )
    if "secret api key required" in cuerpo:
        return (
            "estas usando la publishable key donde va la secret: para "
            "escribir hace falta la Secret key."
        )
    if "permission denied" in cuerpo:
        return "la llave existe pero no tiene permisos sobre esa tabla (RLS)."
    if respuesta.status_code in (401, 403):
        return f"el gateway la rechaza ({respuesta.status_code}): {respuesta.text[:160]}"
    return f"respuesta inesperada ({respuesta.status_code}): {respuesta.text[:160]}"


def _probar(nombre: str, llave: str | None, ruta: str, usar_bearer: bool) -> bool:
    print(f"\n[{nombre}]")
    if not llave:
        print("  FALLA  no esta definida en el .env")
        return False

    print(f"  llave   len={len(llave)} inicio={llave[:10]}...")

    claims = _claims(llave)
    if claims and claims.get("ref") and claims["ref"] != _proyecto(settings.supabase_url):
        print(
            f"  FALLA   es un JWT del proyecto '{claims['ref']}', pero "
            f"SUPABASE_URL apunta a '{_proyecto(settings.supabase_url)}'."
        )
        return False
    if claims and claims.get("role"):
        print(f"  rol     {claims['role']} (JWT)")

    cabeceras = {"apikey": llave}
    if usar_bearer:
        cabeceras["Authorization"] = f"Bearer {llave}"

    try:
        respuesta = httpx.get(
            f"{settings.supabase_url.rstrip('/')}{ruta}",
            headers=cabeceras,
            timeout=TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001 - red caida, no llave mala
        print(f"  FALLA   no se pudo alcanzar el proyecto: {type(exc).__name__}: {exc}")
        print("          revisa SUPABASE_URL y tu conexion.")
        return False

    if respuesta.status_code == 200:
        print(f"  OK      {ruta} -> 200")
        return True

    print(f"  FALLA   {ruta} -> {respuesta.status_code}")
    print(f"          {_motivo(respuesta)}")
    return False


def main() -> int:
    url = settings.supabase_url
    print(f"Proyecto : {_proyecto(url)}")
    print(f"URL      : {url}")

    # La publishable se prueba contra auth (login) y contra el catalogo: es
    # exactamente lo que hara el navegador de un anonimo.
    publica_ok = _probar(
        "SUPABASE_PUBLISHABLE_KEY",
        settings.supabase_publishable_key,
        "/auth/v1/health",
        usar_bearer=False,
    )
    if publica_ok:
        publica_ok = _probar(
            "SUPABASE_PUBLISHABLE_KEY sobre el catalogo",
            settings.supabase_publishable_key,
            "/rest/v1/products?select=id&limit=1",
            usar_bearer=True,
        )

    # La secret es la que usa el backend para escribir: se prueba contra REST,
    # que es donde el gateway distingue publishable de secret.
    secreta_ok = _probar(
        "SUPABASE_SERVICE_ROLE_KEY",
        settings.supabase_service_role_key,
        "/rest/v1/products?select=id&limit=1",
        usar_bearer=True,
    )

    print("\n" + "=" * 62)
    if publica_ok and secreta_ok:
        print("RESULTADO: las dos llaves responden. La app puede arrancar.")
        return 0

    print("RESULTADO: hay llaves malas (ver arriba).")
    if not secreta_ok:
        print(
            "\nEl backend usa SUPABASE_SERVICE_ROLE_KEY para escribir stock y\n"
            "ordenes: sin ella /tienda devuelve 500. Pasos:\n"
            "  1. Supabase > Project Settings > API Keys > copia la Secret key.\n"
            "  2. Pegala en src/fastapi_2026/.env como SUPABASE_SERVICE_ROLE_KEY.\n"
            "  3. Reinicia uvicorn: el cliente admin esta en cache (lru_cache).\n"
            "  4. Verifica: GET /health/db -> ok: true"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
