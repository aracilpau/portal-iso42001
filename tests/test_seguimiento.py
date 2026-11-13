# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Marcar puntos, los que se cumplen solos y el panel."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.seguimiento import Seguimiento

POLITICA = ["5.2.a", "5.2.b", "5.2.c", "5.2.d", "5.2.e", "5.2.f"]


def punto(codigo):
    return next(p for r in guia.requisitos() for p in r.puntos if p.codigo == codigo)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd) as c:
        yield c


# --- Piezas: las cuentas ---

def test_al_principio_no_hay_nada_cumplido():
    est = Seguimiento(set())
    assert est.obligatorios.hechos == 0 and est.obligatorios.total == 27
    assert est.controles.hechos == 0 and est.controles.total == 38
    assert est.recomendados.hechos == 0 and est.recomendados.total == 3


def test_un_requisito_llega_al_100_cuando_estan_todos_sus_puntos():
    est = Seguimiento({"4.3.a", "4.3.b"})
    assert not est.completo("4.3")
    assert est.avance("4.3").hechos == 2 and est.avance("4.3").total == 3  # el 4.3.d no cuenta
    est = Seguimiento({"4.3.a", "4.3.b", "4.3.c"})
    assert est.completo("4.3")
    assert est.avance("4.3").porcentaje == 100
    assert est.obligatorios.hechos == 1


def test_un_recomendado_se_puede_marcar_pero_no_cuenta():
    est = Seguimiento({"4.3.a", "4.3.b", "4.3.c", "4.3.d"})
    assert est.avance("4.3").total == 3
    assert est.recomendados.hechos == 1


def test_un_punto_apoyado_se_marca_solo_y_se_desmarca_solo():
    assert not Seguimiento(set()).cumplido(punto("7.3.a"))
    assert Seguimiento(set(POLITICA)).cumplido(punto("7.3.a"))  # la 5.2 está completa
    sin_uno = set(POLITICA) - {"5.2.c"}
    assert not Seguimiento(sin_uno).cumplido(punto("7.3.a"))  # la 5.2 vuelve atrás


def test_con_varios_apoyos_hacen_falta_todos():
    p = punto("7.4.b")  # se apoya en 5.2 y 7.3
    est = Seguimiento(set(POLITICA))
    assert not est.cumplido(p)
    assert est.faltan(p) == ["7.3"]
    est = Seguimiento(set(POLITICA) | {"7.3.b", "7.3.c"})  # la 7.3.a ya se cumple sola
    assert est.completo("7.3")
    assert est.cumplido(p)


def test_los_puntos_por_sistema_esperan_al_inventario():
    est = Seguimiento({"A.5.4.a"})  # aunque estuviera guardado, no cuenta
    assert not est.cumplido(punto("A.5.4.a"))
    assert not est.completo("A.5.4")


def test_la_4_4_solo_se_completa_con_todos_los_demas():
    est = Seguimiento(set())
    assert not est.completo("4.4")
    assert est.avance("4.4").total == 64


def test_lo_de_un_espacio_no_se_ve_en_otro(bd):
    general = db.espacio(bd, "general")["id"]
    con = db.conectar(bd)
    with con:
        con.execute("INSERT INTO espacio (slug, nombre) VALUES ('otra', 'Otra')")
    con.close()
    otra = db.espacio(bd, "otra")["id"]
    db.marcar(bd, general, "4.3.a", date.today())
    db.guardar_nota(bd, general, "4.3", "La lleva Ana")
    assert db.marcados(bd, general) == {"4.3.a"}
    assert db.marcados(bd, otra) == set()
    assert db.nota(bd, otra, "4.3") == ""


def test_marcar_dos_veces_no_duplica_y_desmarcar_lo_quita(bd):
    general = db.espacio(bd, "general")["id"]
    db.marcar(bd, general, "4.3.a", date.today())
    db.marcar(bd, general, "4.3.a", date.today())
    assert db.marcados(bd, general) == {"4.3.a"}
    db.desmarcar(bd, general, "4.3.a")
    assert db.marcados(bd, general) == set()


# --- Recorridos: desde el navegador ---

def test_marcar_desde_la_ficha_cambia_la_ficha_la_lista_y_el_panel(cliente):
    for p in ("4.3.a", "4.3.b", "4.3.c"):
        r = cliente.post(f"/requisitos/4.3/puntos/{p}/marcar")
        assert r.status_code == 200  # tras la redirección, la ficha
    ficha = cliente.get("/requisitos/4.3").text
    assert "100<small>%</small>" in ficha and "completo" in ficha
    assert "/requisitos/4.3/puntos/4.3.a/desmarcar" in ficha
    lista = cliente.get("/requisitos").text
    assert '<span class="sello s-ok">Completo</span>' in lista
    panel = cliente.get("/").text
    assert "1 de 27 completos" in panel


def test_desmarcar_desde_la_ficha(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    cliente.post("/requisitos/4.3/puntos/4.3.a/desmarcar")
    ficha = cliente.get("/requisitos/4.3").text
    assert "/requisitos/4.3/puntos/4.3.a/marcar" in ficha


def test_la_ficha_explica_cuantos_puntos_se_cumplen_solos(cliente):
    ficha = cliente.get("/requisitos/7.4").text
    assert "De 3 puntos, 2 se cumplen solos al completar otros requisitos; te queda 1 propio." in ficha


def test_un_punto_apoyado_dice_a_que_espera(cliente):
    ficha = cliente.get("/requisitos/7.3").text
    assert "Se marcará solo cuando esté completo: 5.2." in ficha


def test_no_se_pueden_marcar_a_mano_los_apoyados_ni_los_de_sistema(cliente):
    assert cliente.post("/requisitos/7.3/puntos/7.3.a/marcar").status_code == 400
    assert cliente.post("/requisitos/A.5.4/puntos/A.5.4.a/marcar").status_code == 400
    assert cliente.post("/requisitos/4.3/puntos/9.9.z/marcar").status_code == 404


def test_guardar_y_borrar_la_nota(cliente):
    cliente.post("/requisitos/4.3/nota", data={"texto": "El alcance lo revisa Dirección en enero."})
    assert "El alcance lo revisa Dirección en enero." in cliente.get("/requisitos/4.3").text
    cliente.post("/requisitos/4.3/nota", data={"texto": "   "})
    assert "El alcance lo revisa Dirección en enero." not in cliente.get("/requisitos/4.3").text


def test_el_panel_avisa_de_que_los_controles_cuentan_todos(cliente):
    panel = cliente.get("/").text
    assert "Aún no has decidido qué controles del Anexo A aplican" in panel
    assert "Recomendados: 0 de 3" in panel
