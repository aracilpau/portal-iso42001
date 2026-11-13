# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El esqueleto: la guía se carga, la base de datos se crea y el inicio se abre."""
import sqlite3

from fastapi.testclient import TestClient

from guia import datos as guia
from portal import db
from portal.main import crear_app
from conftest import en_portal, entrar


# --- Piezas: la guía ---

def test_la_guia_tiene_65_requisitos_y_162_puntos():
    assert len(guia.filas) == 65
    assert len(guia.C) == 27
    assert len(guia.A) == 38
    assert len(guia.P) == 162


def test_los_datos_de_la_guia_son_coherentes():
    guia.comprobar()  # falla si hay códigos repetidos, apoyos a requisitos que no existen, etc.


def test_el_tipo_de_cada_requisito_sale_de_sus_puntos():
    # Si un requisito tiene un punto de Práctica, el requisito lleva Práctica
    tipos = {f[0]: f[6].split() for f in guia.filas}
    assert "P" in tipos["9.2"]  # por la 9.2.c, la imparcialidad del auditor
    assert tipos["7.3"][:1] == ["P"]  # la 7.3 es entera de Práctica


# --- Piezas: la base de datos ---

def test_la_base_de_datos_se_crea_con_el_espacio_general(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    espacios = db.espacios(ruta)
    assert [e["slug"] for e in espacios] == ["general"]
    assert espacios[0]["nombre"] == "General"


def test_arrancar_dos_veces_no_duplica_el_general(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    db.iniciar(ruta)
    assert len(db.espacios(ruta)) == 1


def test_la_base_de_datos_va_en_una_carpeta_que_crea_ella_misma(tmp_path):
    ruta = tmp_path / "no-existe" / "portal.db"
    db.iniciar(ruta)
    assert ruta.exists()
    con = sqlite3.connect(ruta)
    assert con.execute("SELECT count(*) FROM espacio").fetchone()[0] == 1
    con.close()


# --- Recorrido: abrir el portal ---

def test_el_inicio_se_abre(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        r = cliente.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Lo siguiente" in html  # la lista de lo que pide acción
    assert "Guía cargada" not in html  # era información para nosotros, no para quien lo usa


def test_en_inicio_como_vas_va_antes_que_lo_siguiente(tmp_path):
    # «Cómo vas» es lo más importante, así que se lee primero
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        html = cliente.get("/").text
    assert html.index("<h2>Cómo vas</h2>") < html.index("<h2>Lo siguiente</h2>")


def test_las_paginas_no_se_guardan_en_el_navegador(tmp_path):
    # Con Atrás y Adelante, el navegador enseñaba una copia vieja de la ficha
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        paginas = [cliente.get(u) for u in ("/", "/requisitos", "/requisitos/5.2")]
        estilo = cliente.get("/static/mesa.css")
    assert all(r.headers["cache-control"] == "no-store" for r in paginas)
    assert "no-store" not in estilo.headers.get("cache-control", "")


def test_la_direccion_del_estilo_cambia_con_la_version(tmp_path):
    # Si no, al cambiar el estilo el navegador seguía usando el viejo
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        html = cliente.get("/").text
    assert "/static/mesa.css?v=" in html and "/static/htmx.min.js?v=" in html


def test_el_estilo_se_sirve(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        r = cliente.get("/static/mesa.css")
    assert r.status_code == 200
    assert "prefers-color-scheme: dark" in r.text


# --- El portal de prueba (arrancar-prueba.bat) ---

def test_el_portal_de_prueba_usa_su_carpeta_y_no_toca_datos(tmp_path):
    # Lo que hace arrancar-prueba.bat: otra carpeta de datos y el aviso de prueba
    import os, subprocess, sys
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    carpeta = tmp_path / "datos-prueba"
    env = {**os.environ, "PORTAL_DATOS": str(carpeta), "PORTAL_PRUEBA": "1"}
    codigo = ("from fastapi.testclient import TestClient\n"
              "from portal import config\n"
              "from portal.main import app\n"
              "with TestClient(app) as c: html = c.get('/').text\n"
              "print(config.DATOS, config.PRUEBA, 'marca-prueba' in html, sep='|')")
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=raiz, env=env, capture_output=True,
                            text=True, check=True).stdout.strip().splitlines()[-1]
    assert salida == f"{carpeta}|True|True"
    # Se crea ahí, no en datos/: las cuentas (con el usuario de prueba) y el General
    assert (carpeta / "cuentas.db").exists() and (carpeta / "general" / "portal.db").exists()


def test_el_portal_de_siempre_no_dice_prueba(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        html = cliente.get("/").text
    assert "marca-prueba" not in html and "<title>PRUEBA" not in html
    with en_portal(tmp_path / "general" / "portal.db", prueba=True) as cliente:
        html = cliente.get("/").text
    assert ">PRUEBA</span>" in html and "<title>PRUEBA · " in html
