"""Primer ingreso: un solo paso de perfil y despues, la tienda.

El menu de perfil (empleo, estudios, banco) viene del proyecto base y no tiene
nada que ver con comprar ropa. Como peaje eterno es un error de producto: cada
login aterrizaba en un formulario de recursos humanos. Aqui se define la regla
unica del paso:

    se pide UNA vez; despues el login va directo a /tienda.

La marca vive en ``app_metadata`` y no en ``user_metadata`` porque
``user_metadata`` la edita el propio usuario desde el cliente: si la marca
fuera editable, cualquiera podria saltarse el paso o reactivarlo. Pasa lo
mismo que con el rol (ver ``api/deps.user_is_admin``).

Principio de diseno que manda aqui: **ante un error de base, se sigue a la
tienda**. Un fallo de configuracion no puede disfrazarse de "te falta el
perfil" y encerrar al usuario en un formulario que tampoco va a poder guardar.
"""

from __future__ import annotations

from supabase import Client

# Seccion del formulario -> tabla donde queda guardada.
SECCIONES = {
    "empleo": "employment_details",
    "estudios": "education_records",
    "banco": "banking_info",
}

CLAVE = "onboarding_visto"


def progreso(db: Client, user_id: str) -> dict[str, bool]:
    """Que secciones ya tienen fila guardada para este usuario.

    A diferencia del resto del servicio, esta funcion NO se come los errores:
    quien decide necesita distinguir "no hay datos" de "no pude preguntar".
    """
    estado: dict[str, bool] = {}
    for seccion, tabla in SECCIONES.items():
        filas = (
            db.table(tabla)
            .select("profile_id")
            .eq("profile_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        estado[seccion] = bool(filas)
    return estado


def perfil_completo(db: Client, user_id: str) -> bool:
    """True solo si las tres secciones tienen datos."""
    return all(progreso(db, user_id).values())


def _metadata(db: Client, user_id: str) -> dict:
    usuario = db.auth.admin.get_user_by_id(user_id).user
    return dict(getattr(usuario, "app_metadata", None) or {})


def ya_vio_el_paso(db: Client, user_id: str) -> bool:
    return bool(_metadata(db, user_id).get(CLAVE))


def marcar_visto(db: Client, user_id: str) -> None:
    """Escribe la marca sin pisar el resto de ``app_metadata``.

    Se manda el mapa completo ya fusionado en vez de solo ``{CLAVE: True}``:
    si GoTrue reemplazara en lugar de fusionar, mandar solo la clave borraria
    el rol del usuario. El mapa fusionado funciona en los dos casos, y asi el
    codigo no depende de una semantica que no controlamos.
    """
    actual = _metadata(db, user_id)
    if actual.get(CLAVE):
        return  # idempotente: no se escribe si ya estaba
    db.auth.admin.update_user_by_id(user_id, {"app_metadata": {**actual, CLAVE: True}})


def debe_hacer_onboarding(db: Client, user_id: str) -> bool:
    """True solo si hay certeza de que el paso esta pendiente.

    Cualquier error (llave invalida, red, tabla ausente) devuelve False: la
    tienda es lo que el usuario vino a buscar, no un formulario bloqueado.
    """
    try:
        if ya_vio_el_paso(db, user_id):
            return False
        return not perfil_completo(db, user_id)
    except Exception as exc:  # noqa: BLE001 - se degrada, no se propaga
        print(f"⚠️  No se pudo evaluar el onboarding, se sigue a la tienda: {exc}")
        return False
