# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El portal de verdad, con todo en el MySQL.

Estas pruebas no tocan el MySQL de verdad: comprueban el traductor, el «sin conexión», la reserva de los avisos y el
portal local. El recorrido en el MySQL de verdad lo hace `scripts/probar_mysql.py`, que se lanza a mano.
"""
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import EnvioDeMentira, en_portal
from portal import avisos, config, db, servidor
from portal.main import crear_app

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cuentas as programa  # noqa: E402  (scripts/cuentas.py)

LUNES = date(2026, 10, 5)


# --- Piezas: el traductor ---

@pytest.mark.parametrize("sqlite, mysql", [
    ("SELECT * FROM nota WHERE espacio_id = ? AND requisito = ?",
     "SELECT * FROM nota WHERE espacio_id = %s AND requisito = %s"),
    ("INSERT OR IGNORE INTO miembro (usuario_id, empresa) VALUES (?, ?)",
     "INSERT IGNORE INTO miembro (usuario_id, empresa) VALUES (%s, %s)"),
    ("INSERT OR REPLACE INTO revision (a, b) VALUES (?, ?)", "REPLACE INTO revision (a, b) VALUES (%s, %s)"),
    ("INSERT INTO plazo (espacio_id, requisito, meses) VALUES (?, ?, ?) "
     "ON CONFLICT (espacio_id, requisito) DO UPDATE SET meses = excluded.meses",
     "INSERT INTO plazo (espacio_id, requisito, meses) VALUES (%s, %s, %s) "
     "ON DUPLICATE KEY UPDATE meses = VALUES(meses)"),
    ("SELECT * FROM usuario ORDER BY nombre COLLATE NOCASE", "SELECT * FROM usuario ORDER BY nombre"),
])
def test_el_traductor_pasa_cada_orden_al_dialecto_del_mysql(sqlite, mysql):
    assert servidor.traducir(sqlite, con_valores=True) == mysql


def test_un_tanto_por_ciento_no_se_confunde_con_un_valor():
    assert servidor.traducir("SELECT * FROM nota WHERE texto LIKE '50%' AND id = ?", True) == \
        "SELECT * FROM nota WHERE texto LIKE '50%%' AND id = %s"
    assert servidor.traducir("SELECT * FROM espacio WHERE slug LIKE 'zz%'", False) == \
        "SELECT * FROM espacio WHERE slug LIKE 'zz%'"


def test_la_fecha_de_una_decision_se_decide_antes_de_cambiar_aplica():
    # El MySQL hace los cambios de izquierda a derecha: si «aplica» fuera antes, la fecha nunca cambiaría
    import inspect
    texto = inspect.getsource(db.decidir)
    assert texto.index("decidido_en = CASE") < texto.index("aplica = excluded.aplica")


# --- Piezas: secretos.env ---

def test_sin_secretos_lo_dice(tmp_path):
    s = servidor.leer(tmp_path / "secretos.env")
    assert s.problema == servidor.FALTA_SECRETOS
    with pytest.raises(servidor.SinConexion, match="Falta el archivo secretos.env"):
        servidor.conectar(s)


def test_secretos_incompleto_lo_dice(tmp_path):
    (tmp_path / "secretos.env").write_text("MYSQL_SERVIDOR=mysql.ejemplo.com\nMYSQL_USUARIO=yo\nMYSQL_CLAVE=\n",
                                           encoding="utf-8")
    assert servidor.leer(tmp_path / "secretos.env").problema.startswith("El archivo secretos.env está incompleto")


def test_secretos_completo(tmp_path):
    (tmp_path / "secretos.env").write_text("# la clave del MySQL\nMYSQL_SERVIDOR=mysql.ejemplo.com\nMYSQL_PUERTO=3307\n"
                                           "MYSQL_USUARIO=yo\nMYSQL_CLAVE=a=b\n", encoding="utf-8")
    assert servidor.leer(tmp_path / "secretos.env") == servidor.Servidor("mysql.ejemplo.com", 3307, "yo", "a=b")


# --- Recorridos: sin conexión ---

def test_sin_secretos_el_portal_lo_dice_en_cada_pagina(tmp_path):
    s = servidor.Servidor(problema=servidor.FALTA_SECRETOS)
    with TestClient(crear_app(tmp_path, servidor=s)) as c:
        for url in ("/entrar", "/", "/requisitos"):
            r = c.get(url)
            assert r.status_code == 503 and "Sin conexión" in r.text and "Falta el archivo secretos.env" in r.text
        # Un botón (htmx): que cambie la página entera, a la que lo explica
        r = c.post("/requisitos/4.1/puntos/4.1.a/marcar", headers={"HX-Request": "true"})
        assert r.headers.get("HX-Redirect") == "/sin-conexion"
        assert "Falta el archivo secretos.env" in c.get("/sin-conexion").text


def test_sin_internet_lo_dice(tmp_path):
    # Un servidor que no contesta (en este mismo ordenador, en un puerto donde no hay nada)
    s = servidor.Servidor("127.0.0.1", 1, "yo", "clave")
    with TestClient(crear_app(tmp_path, servidor=s)) as c:
        r = c.get("/entrar")
    assert r.status_code == 503 and servidor.SIN_CONEXION in r.text


# --- Piezas: la reserva de los avisos ---

@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


def test_reservar_solo_lo_consigue_el_primero(bd):
    e = db.el_espacio(bd)["id"]
    assert db.reservar_ajuste(bd, e, "correo_semana", "", "2026-10-05")       # sin fila todavía
    assert not db.reservar_ajuste(bd, e, "correo_semana", "", "2026-10-05")   # el segundo ya no
    assert db.reservar_ajuste(bd, e, "correo_semana", "2026-10-05", "2026-10-12")
    assert not db.reservar_ajuste(bd, e, "correo_semana", "2026-10-05", "2026-10-12")
    assert db.ajuste(bd, e, "correo_semana", "") == "2026-10-12"


def test_si_otro_ordenador_ya_lo_ha_mandado_no_se_repite(bd, monkeypatch):
    e = db.el_espacio(bd)["id"]
    for clave, valor in ((avisos.ACTIVADOS, "1"), (avisos.DESDE, "2026-01-01"), (avisos.PARA, "pau@empresa.com"),
                         (avisos.MANDADO_MES, "2026-10-01")):
        db.guardar_ajuste(bd, e, clave, valor)
    reservar = db.reservar_ajuste

    def otro_llega_antes(ruta, espacio_id, clave, antes, ahora):
        # Entre que este ordenador mira qué toca y lo reserva, otro lo ha reservado y mandado
        reservar(ruta, espacio_id, clave, antes, ahora)
        return reservar(ruta, espacio_id, clave, antes, ahora)
    monkeypatch.setattr(db, "reservar_ajuste", otro_llega_antes)
    envio = EnvioDeMentira()
    avisos.ejecutar(bd.parent.parent, LUNES, envio)
    assert envio.correos == [] and envio.notificaciones == []
    assert db.ajuste(bd, e, avisos.MANDADO_SEMANA, "") == "2026-10-05"


def test_si_el_correo_no_sale_la_reserva_se_deshace(bd):
    e = db.el_espacio(bd)["id"]
    for clave, valor in ((avisos.ACTIVADOS, "1"), (avisos.DESDE, "2026-01-01"), (avisos.PARA, "pau@empresa.com"),
                         (avisos.MANDADO_MES, "2026-10-01")):
        db.guardar_ajuste(bd, e, clave, valor)
    avisos.ejecutar(bd.parent.parent, LUNES, EnvioDeMentira(falla="No hay Outlook clásico."))
    assert db.ajuste(bd, e, avisos.MANDADO_SEMANA, "") == ""
    assert db.ajuste(bd, e, avisos.MANDADO_MES, "") == "2026-10-01"


def test_todos_los_ajustes_de_una_vez(bd):
    e = db.el_espacio(bd)["id"]
    db.guardar_ajuste(bd, e, "empresa.nombre", "Ejemplo")
    db.guardar_ajuste(bd, e, "antelacion", "30")
    assert db.ajustes(bd, e) == {"empresa.nombre": "Ejemplo", "antelacion": "30"}


# --- Recorridos: dos formas de arrancar ---

def test_el_portal_local_lo_dice_en_la_cabecera(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as c:
        html = c.get("/").text
    assert "marca-local" in html and "<title>LOCAL · " in html


def test_el_de_prueba_no_dice_local(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db", prueba=True) as c:
        html = c.get("/").text
    assert "marca-local" not in html and "PRUEBA" in html


def test_el_programa_de_cuentas_va_al_mysql_salvo_que_se_diga_local(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SECRETOS", tmp_path / "no-esta.env")
    monkeypatch.setattr(config, "DATOS_LOCAL", tmp_path / "datos")
    monkeypatch.setattr(config, "DATOS_SERVIDOR", tmp_path / "datos-servidor")
    with pytest.raises(servidor.SinConexion, match="Falta el archivo secretos.env"):
        programa.main(["empresas"])
    assert "General" in programa.main(["--local", "empresas"])
    assert (tmp_path / "datos" / "cuentas.db").exists()


def test_la_conexion_con_el_mysql_se_cifra_si_el_servidor_lo_permite():
    # pymysql cifra solo (la 1.2.3, la mínima de requirements.txt, ya lo hace) si no se le dice nada; el portal no le dice nada. Si una versión
    # nueva dejara de hacerlo, esta prueba avisa. Sin conectar a ningún MySQL (defer_connect)
    import pymysql
    con = pymysql.connect(host="mibase.ejemplo.com", user="portal", password="x", database="iso42001",
                          defer_connect=True)
    assert con.ssl, "pymysql ya no cifra por su cuenta: hay que pedírselo en servidor.py e instalar.py"
