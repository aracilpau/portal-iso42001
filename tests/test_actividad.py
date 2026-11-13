# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""«Actividad»: el registro de lo que se hace en el portal."""
import re
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from portal import db
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 3, 15)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


def lineas(cliente, requisito=""):
    """Las líneas de «Actividad», en texto llano y en orden (lo más reciente primero). Sin quién lo hizo: eso se
    comprueba aparte, en test_quien.py."""
    html = cliente.get("/actividad" + (f"?requisito={requisito}" if requisito else "")).text
    # El día va en su propia fila, encima de las de ese día; aquí se pone delante de cada una
    lineas, dia = [], ""
    for clase, f in re.findall(r'<li class="registro-(dia|fila)">(.*?)</li>', html, re.S):
        f = re.sub(r'<span class="registro-quien">.*?</span>', "", f, flags=re.S)
        texto = " ".join(re.sub(r"<[^>]+>", " ", f).split())
        if clase == "dia":
            dia = texto
        else:
            lineas.append(f"{dia} {texto}")
    return lineas


def subir(cliente, punto, nombre, contenido=b"x"):
    codigo = punto.rsplit(".", 1)[0]
    return cliente.post(f"/requisitos/{codigo}/puntos/{punto}/archivos",
                        files=[("archivos", (nombre, contenido, "application/pdf"))])


# --- Piezas ---

def test_apuntar_y_leer_lo_mas_reciente_primero(bd):
    e = db.espacio(bd, "general")["id"]
    db.apuntar(bd, e, datetime(2026, 3, 15, 10, 0), "marcado", requisito="4.3", punto="4.3.a")
    db.apuntar(bd, e, datetime(2026, 3, 15, 11, 0), "subido", requisito="5.2", punto="5.2.a", detalle="a.pdf")
    assert [f["accion"] for f in db.actividad(bd, e)] == ["subido", "marcado"]
    assert [f["accion"] for f in db.actividad(bd, e, "4.3")] == ["marcado"]


# --- Recorridos ---

def test_sin_nada_hecho_la_pagina_lo_dice(cliente):
    html = cliente.get("/actividad").text
    assert "Aún no hay actividad." in html and 'href="/actividad"' in html  # y está en el menú


def test_los_puntos_quedan_apuntados(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    cliente.post("/requisitos/4.3/puntos/4.3.a/renovar")
    cliente.post("/requisitos/4.3/puntos/4.3.a/desmarcar")
    assert [l.split(" ", 2)[2] for l in lineas(cliente)] == [
        "4.3.a desmarcado", "4.3.a renovado", "4.3.a marcado como cumplido"]
    assert lineas(cliente)[0].startswith("15/03/2026 ")  # con el día y la hora


def test_los_archivos_quedan_apuntados_con_su_nombre(cliente):
    subir(cliente, "5.2.a", "politica.pdf")
    cliente.post("/requisitos/5.2/puntos/5.2.a/archivos/politica.pdf/quitar")
    cliente.post("/requisitos/5.2/historial/5.2.a - 2026-03-15 - politica.pdf/borrar")
    textos = lineas(cliente)
    assert "borrado para siempre de versiones anteriores · 5.2.a - 2026-03-15 - politica.pdf" in textos[0]
    assert "5.2.a archivo quitado: pasa a versiones anteriores · politica.pdf" in textos[1]
    assert "5.2.a archivo subido · politica.pdf" in textos[2]


def test_reabrir_apunta_el_motivo_y_la_situacion(cliente):
    cliente.post("/requisitos/7.2/puntos/7.2.a/marcar")
    cliente.post("/eventos/persona", data={"requisitos": ["7.2"]})
    textos = lineas(cliente)
    assert "ha pasado algo · Persona nueva o cambio de puesto · reabiertos 7.2" in textos[0]
    assert "7.2 reabierto · ha pasado algo: persona nueva o cambio de puesto" in textos[1]


def test_la_situacion_queda_apuntada_aunque_no_se_reabra_nada(cliente):
    cliente.post("/eventos/fuera", data={})
    assert [l.split(" ", 2)[2] for l in lineas(cliente)] == ["ha pasado algo · Cambio de fuera · nada que reabrir"]


def test_inventario_y_declaracion_quedan_apuntados(cliente):
    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    x = r.url.path.rsplit("/", 1)[1]
    cliente.post(f"/inventario/{x}", data={"nombre": "ChatGPT Plus", "tipo": "herramienta"})
    cliente.post(f"/inventario/{x}/retirar")
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    textos = lineas(cliente)
    assert "A.10.4 decidido: no aplica · Sin clientes con IA." in textos[0]
    assert "ChatGPT Plus sistema retirado" in textos[1]
    assert "ChatGPT Plus ficha del sistema guardada · antes se llamaba «ChatGPT»" in textos[2]
    assert "ChatGPT sistema dado de alta" in textos[3]


def test_lo_que_falla_no_se_apunta(cliente):
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": ""})  # falta el porqué
    cliente.post("/requisitos/7.3/puntos/7.3.a/marcar")                     # se cumple solo: no se marca
    assert lineas(cliente) == []


def test_el_filtro_por_requisito(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    subir(cliente, "5.2.a", "politica.pdf")
    html = cliente.get("/actividad").text
    assert '<option value="4.3"' in html and '<option value="5.2"' in html
    assert '<option value="4.1"' not in html  # solo los que tienen algo
    assert [l.split(" ", 2)[2] for l in lineas(cliente, "4.3")] == ["4.3.a marcado como cumplido"]
