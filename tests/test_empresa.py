# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El cuestionario, en la página «Empresa» y paso a paso."""
import re

import pytest
from fastapi.testclient import TestClient

from conftest import USUARIO, entrar, preparar_cuentas
from guia import datos as guia_datos
from portal import cuentas, db
from portal import guia as guia_portal
from portal.main import crear_app

HX = {"HX-Request": "true"}
LUIS = ("luis@ejemplo.com", "Luis", "clave-de-luis")


@pytest.fixture
def datos(tmp_path):
    datos = preparar_cuentas(tmp_path / "datos")
    cuentas.crear_usuario(datos, *LUIS)
    cuentas.crear_empresa(datos, "Lambda")
    cuentas.asignar(datos, USUARIO[0], "Lambda")
    cuentas.asignar(datos, LUIS[0], "Lambda")
    return datos


@pytest.fixture
def portal(datos):
    with TestClient(crear_app(datos)) as c:
        yield c


@pytest.fixture
def dentro(portal, datos):
    """Ya dentro de Lambda, con el paso a paso visto, para trabajar en «Empresa»."""
    db.iniciar(cuentas.bd_de(datos, "lambda"))
    db.guardar_ajuste(cuentas.bd_de(datos, "lambda"), 1, "cuestionario_visto", "1")
    return entrar(portal, "lambda")


def bloque_5_escondido(html):
    """Si la etiqueta del bloque 5 lleva «hidden»."""
    return bool(re.search(r'id="bloque-5"[^>]*hidden', html))


def entra(cliente, usuario=USUARIO):
    """Entra en Lambda y dice adónde ha llevado el portal."""
    cliente.post("/entrar", data={"correo": usuario[0], "clave": usuario[2]})
    return cliente.post("/empresas/lambda", follow_redirects=False).headers["location"]


# --- Piezas: las preguntas abiertas de la guía ---

def test_quince_abiertas_en_cinco_bloques_y_doce_si_no_desarrolla():
    assert len(guia_portal.ABIERTAS) == 15 and len(guia_portal.BLOQUES) == 5
    assert all(q.ejemplo and q.requisitos for q in guia_portal.ABIERTAS)
    assert len(guia_portal.abiertas("no")) == 12
    assert len(guia_portal.abiertas("si")) == len(guia_portal.abiertas("nose")) == len(guia_portal.abiertas("")) == 15
    guia_datos.comprobar()


def test_la_comprobacion_pilla_una_clave_repetida(monkeypatch):
    repetida = [(1, "entrena", "¿Otra?", "Ej.", ["4.1"])]  # «entrena» ya es de una de Sí/No
    monkeypatch.setattr(guia_datos, "ABIERTAS", guia_datos.ABIERTAS + repetida)
    with pytest.raises(AssertionError, match="clave abierta ya usada"):
        guia_datos.comprobar()


# --- Recorridos: el paso a paso, la primera vez ---

def test_la_primera_vez_sale_el_paso_a_paso_y_al_terminar_no_vuelve(portal, datos):
    assert entra(portal) == "/empresa/paso/1"
    html = portal.get("/empresa/paso/1").text
    assert "Empresa · paso 1 de 7" in html and "Datos generales" in html
    # «Siguiente» guarda lo escrito
    portal.post("/empresa/paso/1", data={"ir": "siguiente", "r.nombre": "Lambda, S.L.", "r.actividad": ""})
    # Las de Sí/No: sin desarrollar IA, el bloque 5 no sale y quedan 6 pasos
    portal.post("/empresa/paso/2", data={"ir": "siguiente", "r.desarrolla": "no", "r.entrena": "no"})
    assert "Empresa · paso 3 de 6" in portal.get("/empresa/paso/3").text
    # «Saltar este paso» no guarda
    portal.post("/empresa/paso/3", data={"ir": "saltar", "r.uso": "No se guarda"})
    portal.post("/empresa/paso/4", data={"ir": "siguiente", "r.responsables": "Lo lleva Ana."})
    portal.post("/empresa/paso/5", data={"ir": "saltar"})
    r = portal.post("/empresa/paso/6", data={"ir": "siguiente"}, follow_redirects=False)
    assert r.headers["location"] == "/"
    bd = cuentas.bd_de(datos, "lambda")
    assert db.ajuste(bd, 1, "empresa.nombre", "") == "Lambda, S.L."
    assert db.ajuste(bd, 1, "cuestionario.desarrolla", "") == "no"
    assert db.ajuste(bd, 1, "abierta.uso", "") == "" and db.ajuste(bd, 1, "abierta.responsables", "") == "Lo lleva Ana."
    # Ya no vuelve a salir, ni a otro usuario
    portal.post("/salir")
    assert entra(portal, LUIS) == "/"


def test_saltar_el_cuestionario_lo_da_por_visto(portal):
    assert entra(portal) == "/empresa/paso/1"
    r = portal.post("/empresa/paso/1", data={"ir": "terminar"}, follow_redirects=False)
    assert r.headers["location"] == "/"
    portal.post("/salir")
    assert entra(portal) == "/"


def test_si_ya_hay_algo_contestado_no_sale(portal, datos):
    bd = cuentas.bd_de(datos, "lambda")
    db.iniciar(bd)
    db.guardar_ajuste(bd, 1, "cuestionario.entrena", "no")
    assert entra(portal) == "/"


def test_un_paso_que_no_existe(dentro):
    assert dentro.get("/empresa/paso/0").status_code == 404
    assert dentro.get("/empresa/paso/9").status_code == 404


# --- Recorridos: la página «Empresa» ---

def test_empresa_esta_en_el_menu_y_tiene_todo_junto(dentro):
    html = dentro.get("/empresa").text
    assert 'href="/empresa" class="activa"' in html
    assert 'id="datos-generales"' in html and 'id="cuestionario"' in html
    for q in guia_portal.ABIERTAS:
        assert f'hx-post="/empresa/respuesta/{q.clave}"' in html and f"Ej.: {q.ejemplo}" in html
    assert 'id="bloque-5"' in html and not bloque_5_escondido(html)  # sale mientras no diga que no desarrolla


def test_una_abierta_se_guarda_sola_y_la_lee_el_chat(dentro):
    r = dentro.post("/empresa/respuesta/uso", data={"valor": "  Un asistente en la web.  "}, headers=HX)
    assert "1 de 29 aclaradas" in r.text and "Guardado a las" in r.text
    assert ">Un asistente en la web.</textarea>" in dentro.get("/empresa").text
    assert "¿Para qué usáis la IA y qué os aporta?" in dentro.get("/actividad").text
    assert "¿Para qué usáis la IA y qué os aporta? → Un asistente en la web." in \
        dentro.app.state.consultas_de("lambda").cuestionario()


def test_decir_que_no_desarrolla_esconde_el_bloque_5(dentro):
    r = dentro.post("/empresa/respuesta/desarrolla", data={"valor": "no"}, headers=HX)
    assert bloque_5_escondido(r.text) and re.search(r'id="bloque-5"[^>]*hx-swap-oob="true"', r.text)
    assert bloque_5_escondido(dentro.get("/empresa").text)
    r = dentro.post("/empresa/respuesta/desarrolla", data={"valor": "si"}, headers=HX)
    assert 'id="bloque-5"' in r.text and not bloque_5_escondido(r.text)


# --- Recorridos: al cambiar una respuesta, proponer reabrir ---

def test_al_contestar_por_primera_vez_no_propone_nada(dentro):
    dentro.post("/requisitos/9.2/puntos/9.2.a/marcar")
    r = dentro.post("/empresa/respuesta/auditoria", data={"valor": "Una consultora."}, headers=HX)
    assert "/empresa/reabrir/" not in r.text


def test_al_cambiar_una_abierta_propone_reabrir_y_reabre_lo_elegido(dentro):
    dentro.post("/empresa/respuesta/auditoria", data={"valor": "Una consultora."}, headers=HX)
    dentro.post("/requisitos/9.2/puntos/9.2.a/marcar")
    r = dentro.post("/empresa/respuesta/auditoria", data={"valor": "Alguien de calidad."}, headers=HX)
    assert 'action="/empresa/reabrir/auditoria"' in r.text and 'name="requisitos" value="9.2" checked' in r.text
    r = dentro.post("/empresa/reabrir/auditoria", data={"requisitos": ["9.2"]})
    assert "Reabierto: 9.2." in r.text
    assert "- 9.2.a: pendiente" in dentro.app.state.consultas_de("lambda").estado_requisito("9.2")
    assert "por cambiar «¿Quién haría la auditoría interna?»" in dentro.get("/actividad").text


def test_al_cambiar_una_de_si_no_propone_sus_controles(dentro):
    dentro.post("/empresa/respuesta/entrena", data={"valor": "si"}, headers=HX)
    dentro.post("/requisitos/A.7.2/puntos/A.7.2.a/marcar")
    r = dentro.post("/empresa/respuesta/entrena", data={"valor": "no"}, headers=HX)
    assert 'action="/empresa/reabrir/entrena"' in r.text and 'value="A.7.2" checked' in r.text


def test_si_no_hay_nada_que_reabrir_no_sale_la_lista(dentro):
    dentro.post("/empresa/respuesta/auditoria", data={"valor": "Una consultora."}, headers=HX)
    r = dentro.post("/empresa/respuesta/auditoria", data={"valor": "Otra."}, headers=HX)
    assert "/empresa/reabrir/" not in r.text
    # Los datos generales no reabren nada
    dentro.post("/empresa/respuesta/nombre", data={"valor": "A"}, headers=HX)
    assert "/empresa/reabrir/" not in dentro.post("/empresa/respuesta/nombre", data={"valor": "B"}, headers=HX).text
    assert dentro.post("/empresa/reabrir/nombre", data={}).status_code == 404
