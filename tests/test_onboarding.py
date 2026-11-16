"""El paso de perfil del primer ingreso.

Regla de negocio bajo prueba: se pide UNA vez y despues el login aterriza en
la tienda. Dos cosas se verifican aqui, y la segunda importa tanto como la
primera:

  * que el paso se cierre de verdad (marca en app_metadata, no se vuelve a
    preguntar, y marcar no pisa el rol del usuario);
  * que un fallo de base NO se disfrace de "te falta el perfil", porque eso
    dejaria al usuario atrapado en un formulario que tampoco puede guardar.
"""

from __future__ import annotations

import pytest

from fastapi_2026.services.auth import AuthService
from fastapi_2026.services.onboarding import (
    SECCIONES,
    debe_hacer_onboarding,
    marcar_visto,
    perfil_completo,
    progreso,
    ya_vio_el_paso,
)

from .fakes import FakeDB

TABLAS = tuple(SECCIONES.values())


def llenar_perfil(db: FakeDB, user_id: str = "u1", cuantas: int = 3) -> None:
    """Guarda N de las tres secciones del perfil."""
    for tabla in TABLAS[:cuantas]:
        db.table(tabla).insert({"profile_id": user_id}).execute()


class AdminCaido:
    """Simula la llave invalida: cualquier llamada a auth.admin revienta."""

    def get_user_by_id(self, user_id: str):
        raise RuntimeError("401 Unregistered API key")

    def update_user_by_id(self, user_id: str, payload: dict):
        raise RuntimeError("401 Unregistered API key")


class TestProgreso:
    def test_reporta_cada_seccion(self, db):
        assert progreso(db, "u1") == {seccion: False for seccion in SECCIONES}

    def test_una_seccion_guardada_no_hace_el_perfil_completo(self, db):
        llenar_perfil(db, cuantas=1)
        assert perfil_completo(db, "u1") is False

    def test_las_tres_secciones_lo_completan(self, db):
        llenar_perfil(db)
        assert perfil_completo(db, "u1") is True

    def test_no_confunde_el_perfil_de_otro_usuario(self, db):
        llenar_perfil(db, user_id="u2")
        assert perfil_completo(db, "u1") is False


class TestDecision:
    def test_usuario_nuevo_ve_el_paso(self, db):
        assert debe_hacer_onboarding(db, "u1") is True

    def test_perfil_completo_ya_no_lo_ve(self, db):
        llenar_perfil(db)
        assert debe_hacer_onboarding(db, "u1") is False

    def test_la_marca_cierra_el_paso_aunque_falte_llenarlo(self, db):
        marcar_visto(db, "u1")
        assert ya_vio_el_paso(db, "u1") is True
        assert debe_hacer_onboarding(db, "u1") is False

    def test_una_base_caida_no_encierra_al_usuario(self, db):
        """Sin base no se puede saber si falta el perfil: se sigue a la tienda."""
        db.tables["employment_details"] = None  # cualquier uso revienta

        assert debe_hacer_onboarding(db, "u1") is False


class TestMarca:
    def test_marcar_no_pisa_el_rol(self, db):
        db.users["u9"]["app_metadata"] = {"role": "admin"}

        marcar_visto(db, "u9")

        assert db.users["u9"]["app_metadata"] == {
            "role": "admin",
            "onboarding_visto": True,
        }

    def test_marcar_dos_veces_es_inofensivo(self, db):
        marcar_visto(db, "u1")
        marcar_visto(db, "u1")

        assert db.users["u1"]["app_metadata"]["onboarding_visto"] is True

    def test_si_no_se_puede_marcar_el_error_sube(self, db):
        """`marcar_visto` reporta; el que decide que hacer es el llamador."""
        db.auth.admin = AdminCaido()

        with pytest.raises(RuntimeError):
            marcar_visto(db, "u1")


class TestRutaBienvenida:
    def test_primer_ingreso_muestra_el_formulario_con_salida(self, client):
        respuesta = client.get("/bienvenida")

        assert respuesta.status_code == 200
        html = respuesta.text
        # Las dos salidas posibles: llenarlo o saltarlo.
        assert 'action="/bienvenida/saltar"' in html
        assert 'href="/tienda"' in html
        assert "Paso único de perfil" in html

    def test_con_el_perfil_completo_va_directo_a_la_tienda(self, client, db):
        llenar_perfil(db)

        respuesta = client.get("/bienvenida", follow_redirects=False)

        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/tienda"

    def test_saltar_marca_y_no_vuelve_a_preguntar(self, client, db):
        respuesta = client.post("/bienvenida/saltar", follow_redirects=False)

        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/tienda"
        assert db.users["u1"]["app_metadata"]["onboarding_visto"] is True
        siguiente = client.get("/bienvenida", follow_redirects=False)
        assert siguiente.headers["location"] == "/tienda"

    def test_el_menu_normal_ya_no_muestra_el_aviso(self, client):
        """El aviso es del primer ingreso, no de la pagina de perfil."""
        html = client.get("/menu").text

        assert "Paso único de perfil" not in html
        assert 'action="/bienvenida/saltar"' not in html
        assert 'src="/static/images/logo-web.png"' in html

        logo = client.get("/static/images/logo-web.png")
        assert logo.status_code == 200
        assert logo.headers["content-type"] == "image/png"

    def test_anonimo_va_al_login_en_vez_de_recibir_un_401(self, anon_client):
        respuesta = anon_client.get("/bienvenida", follow_redirects=False)

        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/login"


class TestGuardadoDelPerfil:
    BANCO = {
        "bank_name": "Banco Test",
        "account_type": "ahorro",
        "account_number": "0000",
    }

    def test_guardar_la_ultima_seccion_cierra_el_paso(self, client, db):
        llenar_perfil(db, cuantas=2)

        respuesta = client.post(
            "/profile/banking", data=self.BANCO, follow_redirects=False
        )

        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/bienvenida"
        assert db.users["u1"]["app_metadata"]["onboarding_visto"] is True

    def test_guardar_una_seccion_suelta_pide_el_resto(self, client, db):
        respuesta = client.post(
            "/profile/banking", data=self.BANCO, follow_redirects=False
        )

        assert respuesta.headers["location"] == "/bienvenida"
        assert ya_vio_el_paso(db, "u1") is False


class TestLogin:
    def test_el_login_aterriza_en_el_paso_y_no_en_el_menu(self, anon_client, monkeypatch):
        class SesionFalsa:
            access_token = "access"
            refresh_token = "refresh"

        async def sign_in_falso(self, email: str, password: str):
            return SesionFalsa()

        monkeypatch.setattr(AuthService, "sign_in", sign_in_falso)

        respuesta = anon_client.post(
            "/login",
            data={"email": "u1@test.dev", "password": "secreta"},
            follow_redirects=False,
        )

        assert respuesta.status_code == 303
        assert respuesta.headers["location"] == "/bienvenida"
