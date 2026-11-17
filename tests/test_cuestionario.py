# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El cuestionario de la empresa."""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from guia import datos
from portal import db
from portal import guia as guia_portal
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 3, 15)
HX = {"HX-Request": "true"}


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


def pregunta(html, clave):
    """El trozo de la página con una pregunta del cuestionario."""
    i = html.index(f'id="pregunta-{clave}"')
    return html[i:html.index("</li>", i)]


# --- Piezas: las preguntas de la guía ---

def test_hay_diez_preguntas_y_cuatro_datos():
    assert len(guia_portal.PREGUNTAS) == 10 and len(guia_portal.DATOS_EMPRESA) == 4


def test_cada_control_tiene_su_pregunta_o_aplica_casi_siempre():
    controles = {a[0] for a in datos.A}
    por_pregunta = {c for q in guia_portal.PREGUNTAS for c in q.controles}
    assert por_pregunta | set(guia_portal.CASI_SIEMPRE) == controles
    datos.comprobar()  # la comprobación de la guía también lo vigila


def test_la_comprobacion_pilla_un_control_sin_pregunta(monkeypatch):
    monkeypatch.setattr(datos, "CASI_SIEMPRE", [c for c in datos.CASI_SIEMPRE if c != "A.9.4"])
    with pytest.raises(AssertionError, match="A.9.4"):
        datos.comprobar()


# --- Recorridos: en «Empresa» ---

def test_esta_en_empresa_y_la_declaracion_dice_cuanto_falta(cliente):
    html = cliente.get("/empresa").text
    assert "0 de 29 preguntas contestadas" in html  # 4 datos, 10 de Sí/No y 15 abiertas
    for q in guia_portal.PREGUNTAS:
        assert f'hx-post="/empresa/respuesta/{q.clave}"' in html
    assert 'placeholder="Ej.: Ejemplo, S.L."' in html
    declaracion = cliente.get("/declaracion").text
    assert "Quedan 14 de las 14 respuestas de" in declaracion and 'href="/empresa#cuestionario"' in declaracion
    assert declaracion.index('id="cuestionario"') < declaracion.index('id="control-A.2.2"')


def test_contestar_se_guarda_solo_y_se_ve_al_volver(cliente, bd):
    r = cliente.post("/declaracion/cuestionario/entrena", data={"valor": "no"}, headers=HX)
    assert 'id="cuestionario-estado"' in r.text and "1 de 29 preguntas contestadas" in r.text and "Guardado a las" in r.text
    assert 'value="no" checked' in pregunta(cliente.get("/empresa").text, "entrena")
    cliente.post("/declaracion/cuestionario/nombre", data={"valor": "Ejemplo, S.L."}, headers=HX)
    assert 'id="empresa-nombre" name="valor" type="text" value="Ejemplo, S.L."' in cliente.get("/empresa").text
    actividad = cliente.get("/actividad").text
    assert "¿Entrenáis o ajustáis modelos con datos vuestros? No" in actividad
    cliente.post("/declaracion/cuestionario/entrena", data={"valor": "no"}, headers=HX)  # sin cambios: no se apunta
    assert cliente.get("/actividad").text.count("¿Entrenáis") == 1


def test_completo_deja_de_avisar_y_no_lo_se_queda_por_aclarar(cliente):
    for q in guia_portal.PREGUNTAS:
        cliente.post(f"/declaracion/cuestionario/{q.clave}", data={"valor": "nose"}, headers=HX)
    for clave, _, _ in guia_portal.DATOS_EMPRESA:
        cliente.post(f"/declaracion/cuestionario/{clave}", data={"valor": "x"}, headers=HX)
    assert "Quedan 10 de las 14 respuestas de" in cliente.get("/declaracion").text
    assert "4 de 29 preguntas contestadas" in cliente.get("/empresa").text
    for q in guia_portal.PREGUNTAS:
        cliente.post(f"/declaracion/cuestionario/{q.clave}", data={"valor": "no"}, headers=HX)
    html = cliente.get("/declaracion").text
    assert "Quedan" not in html[html.index('id="cuestionario"'):html.index("</p>", html.index('id="cuestionario"'))]
    # Sin desarrollar IA, el bloque 5 no cuenta: 4 + 10 + 12 abiertas
    assert "14 de 26 preguntas contestadas" in cliente.get("/empresa").text


def test_el_inventario_sugiere_las_preguntas_1_y_8(cliente):
    sin = cliente.get("/empresa").text
    assert "Según tu inventario" not in sin
    cliente.post("/inventario", data={"nombre": "Asistente", "tipo": "producto"})
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    html = cliente.get("/empresa").text
    desarrolla, proveedores = pregunta(html, "desarrolla"), pregunta(html, "proveedores")
    assert 'value="si" checked' in desarrolla and "Según tu inventario: Asistente es una IA que ofrecéis a clientes." in desarrolla
    assert 'value="si" checked' in proveedores and "ChatGPT es una IA que usa el equipo" in proveedores
    # Contestado a mano, manda lo contestado y la nota desaparece
    r = cliente.post("/declaracion/cuestionario/desarrolla", data={"valor": "no"}, headers=HX)
    assert '<span id="nota-desarrolla" class="cuestionario-nota" hx-swap-oob="true"></span>' in r.text
    desarrolla = pregunta(cliente.get("/empresa").text, "desarrolla")
    assert 'value="no" checked' in desarrolla and "Según tu inventario" not in desarrolla


def test_un_sistema_retirado_no_sugiere(cliente):
    cliente.post("/inventario", data={"nombre": "Asistente", "tipo": "producto"})
    cliente.post("/inventario/1/no-reabrir")
    cliente.post("/inventario/1/retirar")
    assert "Según tu inventario" not in pregunta(cliente.get("/empresa").text, "desarrolla")


def test_respuestas_no_validas(cliente):
    assert cliente.post("/declaracion/cuestionario/entrena", data={"valor": "quizá"}).status_code == 400
    assert cliente.post("/declaracion/cuestionario/raro", data={"valor": "si"}).status_code == 404


def test_contestar_no_toca_la_declaracion(cliente, bd):
    cliente.post("/declaracion/A.7.2", data={"aplica": "si", "porque": "Entrenamos un modelo propio."})
    cliente.post("/declaracion/cuestionario/entrena", data={"valor": "no"}, headers=HX)
    assert db.decisiones(bd, 1)["A.7.2"].aplica is True
