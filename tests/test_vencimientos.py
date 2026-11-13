# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Vencimientos, renovar, reabrir y ajustes de fechas."""
import re
import sqlite3
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.db import Marca
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.seguimiento import (CUMPLIDO, PENDIENTE, VENCE_PRONTO, VENCIDO, Seguimiento,
                                sumar_meses)

POLITICA = ["5.2.a", "5.2.b", "5.2.c", "5.2.d", "5.2.e", "5.2.f"]
DIA = date(2026, 3, 15)          # el día en que se marca en las pruebas
VENCE = date(2027, 3, 15)        # la 5.2 es «una vez y revisar»: vence al año


def punto(codigo):
    return guia.punto(codigo)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


class Reloj:
    """Un «hoy» que se puede adelantar, para simular que pasa el tiempo."""

    def __init__(self, dia):
        self.dia = dia

    def __call__(self):
        return self.dia


@pytest.fixture
def reloj():
    return Reloj(DIA)


@pytest.fixture
def cliente(bd, reloj):
    with en_portal(bd, hoy=reloj) as c:
        yield c


# --- Piezas: los estados según la fecha ---

def test_sumar_meses_cuida_los_meses_cortos():
    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2028, 2, 29), 12) == date(2029, 2, 28)
    assert sumar_meses(date(2026, 11, 10), 12) == date(2027, 11, 10)
    assert sumar_meses(date(2026, 11, 10), 3) == date(2027, 2, 10)


def test_un_punto_pasa_por_los_cuatro_estados():
    marcas = {"5.2.a": Marca(DIA)}
    p = punto("5.2.a")
    assert Seguimiento({}, hoy=DIA).estado(p) == PENDIENTE
    assert Seguimiento(marcas, hoy=VENCE - timedelta(days=31)).estado(p) == CUMPLIDO
    assert Seguimiento(marcas, hoy=VENCE - timedelta(days=30)).estado(p) == VENCE_PRONTO
    assert Seguimiento(marcas, hoy=VENCE).estado(p) == VENCE_PRONTO  # el último día aún vale
    assert Seguimiento(marcas, hoy=VENCE + timedelta(days=1)).estado(p) == VENCIDO


def test_vence_pronto_cuenta_y_vencido_no():
    marcas = {c: Marca(DIA) for c in POLITICA}
    assert Seguimiento(marcas, hoy=VENCE).completo("5.2")
    est = Seguimiento(marcas, hoy=VENCE + timedelta(days=1))
    assert not est.completo("5.2")
    assert est.avance("5.2").hechos == 0


def test_la_antelacion_se_puede_cambiar():
    marcas = {"5.2.a": Marca(DIA)}
    hoy = VENCE - timedelta(days=45)
    assert Seguimiento(marcas, hoy=hoy).estado(punto("5.2.a")) == CUMPLIDO
    assert Seguimiento(marcas, hoy=hoy, antelacion=60).estado(punto("5.2.a")) == VENCE_PRONTO


def test_los_de_solo_por_evento_no_vencen_por_fecha():
    est = Seguimiento({"6.3.c": Marca(DIA)}, hoy=DIA + timedelta(days=3650))
    assert est.vence(punto("6.3.c")) is None
    assert est.estado(punto("6.3.c")) == CUMPLIDO


def test_cambiar_el_plazo_recalcula_salvo_lo_recolocado():
    marcas = {"5.2.a": Marca(DIA), "5.2.b": Marca(DIA, vence_manual=date(2026, 5, 1))}
    est = Seguimiento(marcas, plazo_general=6, hoy=DIA)  # la revisión general, a 6 meses
    assert est.vence(punto("5.2.a")) == date(2026, 9, 15)
    assert est.vence(punto("5.2.b")) == date(2026, 5, 1)
    est = Seguimiento(marcas, plazos={"5.2": None}, hoy=DIA)
    assert est.vence(punto("5.2.a")) is None


def test_un_apoyado_deja_de_cumplirse_si_su_apoyo_vence():
    marcas = {c: Marca(DIA) for c in POLITICA}
    assert Seguimiento(marcas, hoy=VENCE).cumplido(punto("7.3.a"))
    assert not Seguimiento(marcas, hoy=VENCE + timedelta(days=1)).cumplido(punto("7.3.a"))


# --- Piezas: la base de datos ---

def test_renovar_cuenta_desde_hoy_y_olvida_lo_recolocado(bd):
    e = db.espacio(bd, "general")["id"]
    db.marcar(bd, e, "5.2.a", DIA)
    db.recolocar(bd, e, "5.2.a", date(2026, 4, 1))
    assert db.marcas(bd, e)["5.2.a"] == Marca(DIA, date(2026, 4, 1))
    db.renovar(bd, e, "5.2.a", date(2026, 11, 10))
    assert db.marcas(bd, e)["5.2.a"] == Marca(date(2026, 11, 10), None)


def test_una_base_de_datos_de_antes_se_pone_al_dia_sin_perder_nada(tmp_path):
    ruta = tmp_path / "portal.db"
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE espacio (id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL,
                              creado TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE punto_marcado (espacio_id INTEGER NOT NULL, punto TEXT NOT NULL,
                                    marcado_en TEXT NOT NULL DEFAULT (datetime('now')),
                                    PRIMARY KEY (espacio_id, punto));
        INSERT INTO espacio (slug, nombre) VALUES ('general', 'General');
        INSERT INTO punto_marcado (espacio_id, punto, marcado_en) VALUES (1, '5.2.a', '2026-10-01 18:30:00');
    """)
    con.commit()
    con.close()
    db.iniciar(ruta)
    assert db.marcas(ruta, 1) == {"5.2.a": Marca(date(2026, 10, 1))}


def test_los_plazos_y_ajustes_son_de_cada_espacio(bd):
    e = db.espacio(bd, "general")["id"]
    assert db.plazos(bd, e) == {}
    db.guardar_plazo(bd, e, "5.2", 6)
    db.guardar_plazo(bd, e, "9.2", None)
    assert db.plazos(bd, e) == {"5.2": 6, "9.2": None}
    assert db.ajuste(bd, e, "antelacion", "30") == "30"
    db.guardar_ajuste(bd, e, "antelacion", "45")
    assert db.ajuste(bd, e, "antelacion", "30") == "45"


# --- Recorridos: desde el navegador ---

def renovar(ficha):
    """Las clases del botón «Renovar» del primer punto que lo tenga (para ver si está destacado)."""
    return re.search(r'<button class="([^"]*)" type="submit"\s+title="Sigue valiendo', ficha).group(1)


def test_marcar_vencer_y_renovar(cliente, reloj):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    ficha = cliente.get("/requisitos/4.3").text
    assert "Vence el 15/03/2027" in ficha
    assert "/requisitos/4.3/puntos/4.3.a/renovar" in ficha
    assert renovar(ficha) == "boton boton-mini"  # un solo «Renovar», sin destacar

    reloj.dia = date(2027, 3, 1)  # a 14 días de vencer
    ficha = cliente.get("/requisitos/4.3").text
    assert "Vence pronto" in ficha and renovar(ficha) == "boton boton-mini boton-acento"  # destacado
    inicio = cliente.get("/").text  # en «Lo siguiente»
    assert '<span class="sello s-aviso">Vence 15 mar</span>' in inicio and "4.3.a" in inicio

    reloj.dia = date(2027, 3, 20)  # ya vencido
    ficha = cliente.get("/requisitos/4.3").text
    assert "Venció el 15/03/2027: ya no cuenta hasta que se renueve." in ficha
    assert '<span class="sello s-mal">Vencido</span>' in cliente.get("/").text

    cliente.post("/requisitos/4.3/puntos/4.3.a/renovar")
    ficha = cliente.get("/requisitos/4.3").text
    assert "Vence el 20/03/2028" in ficha  # cuenta desde el día en que se renueva
    assert "4.3.a" not in cliente.get("/").text


def test_cambiar_el_plazo_en_ajustes(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    cliente.post("/ajustes/plazo-general", data={"meses": "6"})  # para todos
    assert "Vence el 15/09/2026" in cliente.get("/requisitos/4.3").text
    cliente.post("/ajustes/plazo/4.3", data={"vence": "no"})
    assert "No vence por fecha" in cliente.get("/requisitos/4.3").text
    cliente.post("/ajustes/plazo/4.3", data={"vence": "si"})
    assert "Vence el 15/09/2026" in cliente.get("/requisitos/4.3").text
    assert cliente.post("/ajustes/plazo/4.3", data={"vence": "7"}).status_code == 400
    assert cliente.post("/ajustes/plazo-general", data={"meses": "7"}).status_code == 400
    assert cliente.post("/ajustes/plazo/9.9", data={"vence": "no"}).status_code == 404


def test_cambiar_la_antelacion_en_ajustes(cliente, reloj):
    reloj.dia = date(2025, 5, 15)  # marcada entonces: vence en 61 días
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    reloj.dia = DIA
    assert "Vence pronto" not in cliente.get("/requisitos/4.3").text
    cliente.post("/ajustes/antelacion", data={"dias": "90"})
    assert "Vence pronto" in cliente.get("/requisitos/4.3").text
    assert cliente.post("/ajustes/antelacion", data={"dias": "400"}).status_code == 400


def test_reabrir_un_requisito_devuelve_sus_puntos_a_pendiente(cliente):
    for p in POLITICA:
        cliente.post(f"/requisitos/5.2/puntos/{p}/marcar")
    ficha = cliente.get("/requisitos/5.2").text
    assert "100<small>%</small>" in ficha and 'data-confirmar="/requisitos/5.2/reabrir"' in ficha
    cliente.post("/requisitos/5.2/reabrir")
    ficha = cliente.get("/requisitos/5.2").text
    assert "0 de 6 puntos" in ficha and 'data-confirmar="/requisitos/5.2/reabrir"' not in ficha
    assert "Cumplido" not in cliente.get("/requisitos/7.3").text  # la 7.3.a también cae


def test_solo_se_reabre_lo_que_va_por_evento_o_una_vez_y_revisar(cliente):
    cliente.post("/requisitos/5.1/puntos/5.1.b/marcar")
    assert "¿Ha cambiado algo?</button>" not in cliente.get("/requisitos/5.1").text
    assert cliente.post("/requisitos/5.1/reabrir").status_code == 400


def test_no_se_renueva_lo_que_no_esta_marcado(cliente):
    assert cliente.post("/requisitos/4.3/puntos/4.3.a/renovar").status_code == 400


def test_la_pagina_de_ajustes_se_abre_vacia(cliente):
    ajustes = cliente.get("/ajustes").text
    assert "Aún no hay puntos cumplidos." in ajustes
    assert 'id="plazo-5.2"' in ajustes and 'id="plazo-4.4"' not in ajustes  # la 4.4 no tiene puntos


def test_volver_a_los_plazos_por_defecto(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    assert "Volver a los valores recomendados" not in cliente.get("/ajustes").text
    cliente.post("/ajustes/plazo-general", data={"meses": "6"})
    cliente.post("/ajustes/plazo/6.3", data={"vence": "si"})
    assert "Hay 2 cambios respecto a lo recomendado" in cliente.get("/ajustes").text

    cliente.post("/ajustes/plazos/por-defecto")
    ajustes = cliente.get("/ajustes").text
    assert "Volver a los valores recomendados" not in ajustes and ">cambiado<" not in ajustes
    ficha = cliente.get("/requisitos/4.3").text
    assert "Vence el 15/03/2027" in ficha      # 4.3.a vuelve al año
