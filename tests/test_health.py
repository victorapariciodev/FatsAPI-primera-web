"""Tests del diagnostico de base.

La regla: un fallo de configuracion debe producir una instruccion accionable,
no un 500 mudo. Eso es exactamente lo que se verifica aqui.
"""

from __future__ import annotations

from fastapi_2026.services.health import TABLAS, check_database, clasificar_error


class ErrorFalso(Exception):
    """Imita al APIError de postgrest: trae .message y .code."""

    def __init__(self, mensaje: str, codigo: str | None = None) -> None:
        super().__init__(mensaje)
        self.message = mensaje
        self.code = codigo


class DBQueFalla:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def table(self, nombre: str):
        raise self.error


class TestCheckDatabase:
    def test_esquema_completo_pasa(self, db):
        reporte = check_database(db)

        assert reporte["ok"] is True
        assert reporte["tablas_ok"] == len(TABLAS)
        assert reporte["tablas_total"] == len(TABLAS)
        assert reporte["sugerencia"] is None

    def test_tabla_faltante_apunta_al_sql(self):
        error = ErrorFalso(
            "Could not find the table 'public.products' in the schema cache",
            "PGRST205",
        )
        reporte = check_database(DBQueFalla(error))

        assert reporte["ok"] is False
        assert reporte["tablas_ok"] == 0
        assert "store_schema.sql" in reporte["sugerencia"]

    def test_llave_no_registrada_se_explica(self):
        error = ErrorFalso("Unregistered API key", "401")
        assert "Project Settings" in clasificar_error(error)

    def test_publishable_donde_va_la_secret(self):
        error = ErrorFalso("Secret API key required")
        assert "secret key" in clasificar_error(error)

    def test_error_desconocido_no_se_traga(self):
        assert "RuntimeError" in clasificar_error(RuntimeError("boom"))

    def test_el_motivo_real_puede_venir_en_details_bytes(self):
        """PostgREST deja message='JSON could not be generated' y esconde la
        causa en details. Si no se lee details, el reporte es inutil."""
        error = ErrorFalso("JSON could not be generated", "401")
        error.details = (
            b'{"message":"Unregistered API key","hint":"Double check the '
            b'provided API key as it is not registered for this project."}'
        )

        assert "Project Settings" in clasificar_error(error)


class TestRutaSalud:
    def test_estado_basico_del_servidor(self, anon_client):
        respuesta = anon_client.get("/health")

        assert respuesta.status_code == 200
        assert respuesta.json() == {"status": "ok"}

    def test_no_requiere_sesion(self, anon_client):
        respuesta = anon_client.get("/health/db")

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["ok"] is True
        assert len(cuerpo["checks"]) == len(TABLAS)

    def test_reporta_la_tabla_que_falla(self, anon_client, db):
        original = db.table

        def table_con_fallo(nombre: str):
            if nombre == "orders":
                raise ErrorFalso("permission denied for table orders", "42501")
            return original(nombre)

        db.table = table_con_fallo
        cuerpo = anon_client.get("/health/db").json()

        assert cuerpo["ok"] is False
        assert cuerpo["tablas_ok"] == len(TABLAS) - 1
        fallida = next(c for c in cuerpo["checks"] if not c["ok"])
        assert fallida["tabla"] == "orders"
        assert "permisos" in fallida["detalle"]
