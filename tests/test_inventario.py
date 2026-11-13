# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El inventario de IA y los puntos A.4.2.a a A.4.6.a que se cumplen con la ficha."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.db import Sistema
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.seguimiento import CUMPLIDO, FICHA, PENDIENTE, Seguimiento

DIA = date(2026, 3, 15)
LLENO = {"para_que": "Responde dudas. Responsable: Ana", "datos": "Preguntas de clientes",
         "herramientas": "GPT-4o", "infraestructura": "Azure", "personas": "Equipo de producto"}


def punto(codigo):
    return guia.punto(codigo)


def sistema(id=1, nombre="Chat", tipo="herramienta", retirado=None, **campos):
    valores = {c: "" for c in db.CAMPOS} | campos
    return Sistema(id, nombre, tipo, **valores, actualizado=DIA, retirado=retirado)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


def añadir(cliente, nombre, tipo="herramienta"):
    r = cliente.post("/inventario", data={"nombre": nombre, "tipo": tipo})
    return int(str(r.url).rsplit("/", 1)[1])


# --- Piezas: las cuentas ---

def test_los_puntos_de_la_ficha_son_de_su_clase():
    assert Seguimiento(set()).clase(punto("A.4.3.a")) == FICHA
    assert Seguimiento(set()).clase(punto("A.4.2.b")) != FICHA  # mantenerlo al día: se marca a mano


def test_sin_sistemas_estan_pendientes():
    assert Seguimiento(set()).estado(punto("A.4.3.a")) == PENDIENTE


def test_hace_falta_el_campo_en_todos_los_sistemas_activos():
    uno = sistema(1, "Chat", datos="Preguntas")
    otro = sistema(2, "Copilot")
    est = Seguimiento(set(), sistemas=[uno])
    assert est.estado(punto("A.4.3.a")) == CUMPLIDO
    assert est.estado(punto("A.4.4.a")) == PENDIENTE  # herramientas sin rellenar
    est = Seguimiento(set(), sistemas=[uno, otro])
    assert est.estado(punto("A.4.3.a")) == PENDIENTE
    assert [x.nombre for x in est.faltan_sistemas(punto("A.4.3.a"))] == ["Copilot"]


def test_un_sistema_retirado_no_cuenta():
    uno = sistema(1, "Chat", datos="Preguntas")
    retirado = sistema(2, "Viejo", retirado=DIA)
    assert Seguimiento(set(), sistemas=[uno, retirado]).estado(punto("A.4.3.a")) == CUMPLIDO
    assert Seguimiento(set(), sistemas=[retirado]).estado(punto("A.4.3.a")) == PENDIENTE


def test_la_ficha_completa_completa_los_requisitos_a_4_3_a_a_4_6():
    est = Seguimiento(set(), sistemas=[sistema(**LLENO)])
    for c in ("A.4.3", "A.4.4", "A.4.5", "A.4.6"):
        assert est.completo(c), c
    assert not est.completo("A.4.2")  # le falta A.4.2.b, que es de la empresa


# --- Piezas: la base de datos ---

def test_no_se_repiten_nombres_aunque_cambien_las_mayusculas(bd):
    e = db.espacio(bd, "general")["id"]
    db.crear_sistema(bd, e, "ChatGPT", "herramienta", DIA)
    with pytest.raises(db.NombreRepetido):
        db.crear_sistema(bd, e, "chatgpt", "producto", DIA)


def test_la_ficha_guarda_y_recupera_todo(bd):
    e = db.espacio(bd, "general")["id"]
    i = db.crear_sistema(bd, e, "Asistente", "producto", DIA)
    db.guardar_sistema(bd, e, i, "Asistente web", "producto", LLENO, date(2026, 4, 1))
    x = db.sistema(bd, e, i)
    assert x.nombre == "Asistente web" and x.tipo == "producto"
    assert {c: x.campo(c) for c in db.CAMPOS} == LLENO
    assert x.actualizado == date(2026, 4, 1) and x.completos == 5
    db.retirar_sistema(bd, e, i, DIA)
    assert db.sistema(bd, e, i).retirado == DIA
    db.retirar_sistema(bd, e, i, None)
    assert db.sistema(bd, e, i).retirado is None


# --- Recorridos: desde el navegador ---

def test_añadir_rellenar_y_ver_los_puntos(cliente):
    chat = añadir(cliente, "Chat de la plantilla")
    asistente = añadir(cliente, "Asistente web", "producto")
    lista = cliente.get("/inventario").text
    assert "Chat de la plantilla" in lista and "<b>0/5</b>" in lista

    cliente.post(f"/inventario/{chat}", data={"nombre": "Chat de la plantilla", "tipo": "herramienta", **LLENO})
    cliente.post(f"/inventario/{asistente}", data={"nombre": "Asistente web", "tipo": "producto",
                                                    "datos": "Preguntas de clientes"})
    assert "<b>5/5</b>" in cliente.get("/inventario").text
    a43 = cliente.get("/requisitos/A.4.3").text
    assert "100<small>%</small>" in a43  # los dos tienen «datos»
    a44 = cliente.get("/requisitos/A.4.4").text
    assert "0 de 1 puntos" in a44 and "falta rellenar «Herramientas y modelos» en su ficha" in a44
    assert "Se cumple solo con el campo <strong>«Herramientas y modelos»</strong>" in a44

    cliente.post(f"/inventario/{asistente}/retirar")
    assert "100<small>%</small>" in cliente.get("/requisitos/A.4.4").text  # el que faltaba, retirado
    assert "retirado el 15/03/2026" in cliente.get("/inventario").text
    cliente.post(f"/inventario/{asistente}/activar")
    assert "falta rellenar «Herramientas y modelos» en su ficha" in cliente.get("/requisitos/A.4.4").text


def test_con_el_inventario_vacio_la_ficha_lo_dice(cliente):
    a43 = cliente.get("/requisitos/A.4.3").text
    assert "Añade tus sistemas al" in a43 and "<strong>«Datos»</strong>" in a43


def test_errores_al_añadir_y_al_guardar_no_pierden_lo_escrito(cliente):
    r = cliente.post("/inventario", data={"nombre": "Chat", "tipo": ""})
    assert "Elige si es del producto" in r.text and 'value="Chat"' in r.text
    añadir(cliente, "Chat")
    r = cliente.post("/inventario", data={"nombre": "chat", "tipo": "producto"})
    assert "Ya hay un sistema que se llama «chat»." in r.text
    otro = añadir(cliente, "Copilot")
    r = cliente.post(f"/inventario/{otro}", data={"nombre": "Chat", "tipo": "herramienta", "datos": "Código"})
    assert "Ya hay otro sistema que se llama «Chat»." in r.text and ">Código</textarea>" in r.text


def test_la_ficha_de_un_sistema_que_no_existe_da_404(cliente):
    assert cliente.get("/inventario/999").status_code == 404
    assert cliente.post("/inventario/999/retirar").status_code == 404


def test_guardar_retirar_y_activar_vuelven_a_la_lista_con_un_mensaje(cliente):
    chat = añadir(cliente, "Chat")
    r = cliente.post(f"/inventario/{chat}", data={"nombre": "Chat", "tipo": "herramienta", "datos": "x"})
    assert str(r.url).endswith("/inventario?guardado=Chat") and "Ficha de «Chat» guardada." in r.text
    r = cliente.post(f"/inventario/{chat}/retirar")
    assert "/inventario?retirado=" in str(r.url) and "«Chat» retirado" in r.text
    r = cliente.post(f"/inventario/{chat}/activar")
    assert "«Chat» vuelve a estar activo." in r.text


def test_retirar_y_activar_desde_la_lista(cliente):
    chat = añadir(cliente, "Chat")
    lista = cliente.get("/inventario").text
    assert f'data-confirmar="/inventario/{chat}/retirar"' in lista
    cliente.post(f"/inventario/{chat}/retirar")
    lista = cliente.get("/inventario").text
    assert f'action="/inventario/{chat}/activar"' in lista


def test_cada_campo_de_la_ficha_explica_que_poner(cliente):
    chat = añadir(cliente, "Chat")
    ficha = cliente.get(f"/inventario/{chat}").text
    assert ficha.count('<p class="ayuda">') == 5
    assert "Si es un servicio que ofrecéis, incluye también quién lo usa del lado del cliente." in ficha
