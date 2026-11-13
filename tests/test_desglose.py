# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El desglose por sistema de los puntos por sistema."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.db import Marca, Sistema
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.pruebas import Pruebas
from portal.seguimiento import (APOYADO, CUMPLIDO, PENDIENTE, PROPIO, VENCIDO, Seguimiento, toca)

DIA = date(2026, 3, 15)
POLITICA = ["5.2.a", "5.2.b", "5.2.c", "5.2.d", "5.2.e", "5.2.f"]
CONCIENCIACION = POLITICA + ["7.3.b", "7.3.c"]  # con la 5.2 completa, la 7.3.a se cumple sola


def punto(codigo):
    return guia.punto(codigo)


def sistema(id, nombre, tipo, retirado=None, **campos):
    valores = {c: "" for c in db.CAMPOS} | campos
    return Sistema(id, nombre, tipo, **valores, actualizado=DIA, retirado=retirado)


ASISTENTE = sistema(1, "Asistente", "producto")
CHAT = sistema(2, "ChatGPT", "herramienta")


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


class Reloj:
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


def añadir(cliente, nombre, tipo):
    r = cliente.post("/inventario", data={"nombre": nombre, "tipo": tipo})
    return int(str(r.url).rsplit("/", 1)[1])


def linea(codigo, punto, sid, accion="marcar"):
    return f"/requisitos/{codigo}/puntos/{punto}/sistemas/{sid}/{accion}"


# --- Piezas: a quién le toca cada punto ---

def test_los_de_solo_producto_no_tocan_a_las_herramientas():
    assert toca(punto("A.6.2.2.a"), ASISTENTE) and not toca(punto("A.6.2.2.a"), CHAT)
    assert toca(punto("A.5.4.a"), ASISTENTE) and toca(punto("A.5.4.a"), CHAT)


def test_sin_inventario_quedan_pendientes():
    est = Seguimiento(set())
    assert est.estado(punto("A.5.4.a")) == PENDIENTE
    assert est.estado(punto("A.6.2.2.a")) == PENDIENTE


def test_con_solo_herramientas_los_de_producto_cuentan_como_hechos():
    est = Seguimiento(set(), sistemas=[CHAT])
    assert est.estado(punto("A.6.2.2.a")) == CUMPLIDO
    assert est.estado(punto("A.5.4.a")) == PENDIENTE  # este sí le toca a ChatGPT


# --- Piezas: líneas, puntos y vencimientos ---

def test_el_punto_se_cumple_cuando_lo_estan_todas_sus_lineas():
    est = Seguimiento(set(), sistemas=[ASISTENTE, CHAT], lineas={("A.5.4.a", 1): Marca(DIA)})
    assert est.estado_en(punto("A.5.4.a"), ASISTENTE) == CUMPLIDO
    assert est.estado(punto("A.5.4.a")) == PENDIENTE
    assert [x.nombre for x in est.faltan_sistemas(punto("A.5.4.a"))] == ["ChatGPT"]
    est = Seguimiento(set(), sistemas=[ASISTENTE, CHAT],
                      lineas={("A.5.4.a", 1): Marca(DIA), ("A.5.4.a", 2): Marca(DIA)})
    assert est.estado(punto("A.5.4.a")) == CUMPLIDO and est.completo("A.5.4")


def test_una_linea_vencida_arrastra_al_punto():
    # 8.4 es periódica: vence al año
    lineas = {("8.4.a", 1): Marca(DIA), ("8.4.a", 2): Marca(DIA - timedelta(days=400))}
    est = Seguimiento(set(), sistemas=[ASISTENTE, CHAT], lineas=lineas, hoy=DIA)
    assert est.estado_en(punto("8.4.a"), CHAT) == VENCIDO
    assert est.estado(punto("8.4.a")) == VENCIDO and not est.cumplido(punto("8.4.a"))
    avisos = est.avisos(VENCIDO)
    assert [(a.punto.codigo, a.sistema.nombre) for a in avisos] == [("8.4.a", "ChatGPT")]


def test_un_sistema_retirado_no_tiene_linea():
    viejo = sistema(3, "Viejo", "herramienta", retirado=DIA)
    est = Seguimiento(set(), sistemas=[CHAT, viejo], lineas={("A.5.4.a", 2): Marca(DIA)})
    assert [x.nombre for x in est.sistemas_de(punto("A.5.4.a"))] == ["ChatGPT"]
    assert est.estado(punto("A.5.4.a")) == CUMPLIDO


# --- Piezas: los apoyos por sistema ---

def test_un_apoyo_que_no_toca_al_sistema_no_se_mira():
    # A.9.4.b se apoya en A.6.2.8 (solo producto) y en 7.3 (de empresa)
    est = Seguimiento(set(CONCIENCIACION), sistemas=[ASISTENTE, CHAT])
    assert est.clase_linea(punto("A.9.4.b")) == APOYADO
    assert est.estado_en(punto("A.9.4.b"), CHAT) == CUMPLIDO       # A.6.2.8 no le toca
    assert est.estado_en(punto("A.9.4.b"), ASISTENTE) == PENDIENTE  # a este sí: faltan sus logs
    assert est.faltan_en(punto("A.9.4.b"), ASISTENTE) == ["A.6.2.8"]


def test_un_apoyo_de_empresa_mira_el_requisito_entero():
    est = Seguimiento(set(POLITICA), sistemas=[CHAT])  # 7.3 sin terminar
    assert est.estado_en(punto("A.9.4.b"), CHAT) == PENDIENTE
    assert est.faltan_en(punto("A.9.4.b"), CHAT) == ["7.3"]


def test_un_apoyo_por_sistema_mira_la_linea_del_mismo_sistema():
    # A.9.4.a se apoya en A.4.2 (A.4.2.a por sistema, con la ficha; A.4.2.b de empresa) y en A.9.2
    con_ficha = sistema(2, "ChatGPT", "herramienta", para_que="Redactar correos")
    sin_ficha = sistema(4, "Copilot", "herramienta")
    a92 = [p.codigo for p in guia.requisito("A.9.2").puntos if not p.apoyos]
    est = Seguimiento({"A.4.2.b", *a92}, sistemas=[con_ficha, sin_ficha])
    assert est.estado_en(punto("A.9.4.a"), con_ficha) == CUMPLIDO
    assert est.estado_en(punto("A.9.4.a"), sin_ficha) == PENDIENTE


def test_si_el_control_del_apoyo_no_aplica_la_linea_se_marca_a_mano():
    # 6.1.4.c se apoya en 8.4 y A.5.3
    p = punto("6.1.4.c")
    assert Seguimiento(set(), sistemas=[CHAT]).clase_linea(p) == APOYADO
    est = Seguimiento(set(), sistemas=[CHAT], excluidos={"A.5.3"}, lineas={("6.1.4.c", 2): Marca(DIA)})
    assert est.clase_linea(p) == PROPIO
    assert est.estado_en(p, CHAT) == CUMPLIDO


# --- Piezas: las carpetas por sistema ---

def test_carpetas_al_añadir_renombrar_retirar_y_activar(tmp_path):
    c = Pruebas(tmp_path / "pruebas", "general")
    c.crear([ASISTENTE, CHAT])
    assert (c.base / "A.5.4" / "A.5.4.a" / "ChatGPT").is_dir()
    assert (c.base / "A.6.2.2" / "A.6.2.2.a" / "Asistente").is_dir()
    assert not (c.base / "A.6.2.2" / "A.6.2.2.a" / "ChatGPT").exists()  # solo producto
    assert not (c.base / "A.4.3" / "A.4.3.a" / "ChatGPT").exists()      # el de la ficha no lleva archivos
    c.guardar("A.5.4.a", "evaluacion.pdf", __import__("io").BytesIO(b"x"), CHAT)

    c.renombrar("ChatGPT", "ChatGPT Plus")
    assert (c.base / "A.5.4" / "A.5.4.a" / "ChatGPT Plus" / "evaluacion.pdf").exists()
    plus = sistema(2, "ChatGPT Plus", "herramienta")

    # Al retirarlo, sus archivos van al historial y sus carpetas se quitan
    c.retirar(plus, date(2026, 10, 2))
    assert not (c.base / "A.5.4" / "A.5.4.a" / "ChatGPT Plus").exists()
    assert [a.nombre for a in c.historial("A.5.4")] == ["A.5.4.a - ChatGPT Plus - 2026-10-02 - evaluacion.pdf"]

    # Al volver a activarlo, sus carpetas vuelven, vacías
    c.activar(plus)
    assert (c.base / "A.5.4" / "A.5.4.a" / "ChatGPT Plus").is_dir()
    assert c.archivos("A.5.4.a", plus) == []


def test_el_historial_lleva_el_sistema_en_el_nombre(tmp_path):
    import io
    c = Pruebas(tmp_path / "pruebas", "general")
    c.crear([CHAT])
    c.guardar("A.5.4.a", "evaluacion.pdf", io.BytesIO(b"x"), CHAT)
    assert c.quitar("A.5.4.a", "evaluacion.pdf", DIA, CHAT) == "A.5.4.a - ChatGPT - 2026-03-15 - evaluacion.pdf"


# --- Recorridos: desde el navegador ---

def test_marcar_una_linea_y_luego_la_otra(cliente):
    asistente = añadir(cliente, "Asistente", "producto")
    chat = añadir(cliente, "ChatGPT", "herramienta")
    assert cliente.post(linea("A.5.4", "A.5.4.a", asistente)).status_code == 200
    ficha = cliente.get("/requisitos/A.5.4").text
    assert "1 de 2 sistemas" in ficha and "0 de 1 puntos" in ficha
    cliente.post(linea("A.5.4", "A.5.4.a", chat))
    ficha = cliente.get("/requisitos/A.5.4").text
    assert "2 de 2 sistemas" in ficha and "100<small>%</small>" in ficha
    cliente.post(linea("A.5.4", "A.5.4.a", chat, "desmarcar"))
    assert "1 de 2 sistemas" in cliente.get("/requisitos/A.5.4").text


def test_los_de_solo_producto_solo_enseñan_la_linea_del_producto(cliente):
    asistente = añadir(cliente, "Asistente", "producto")
    chat = añadir(cliente, "ChatGPT", "herramienta")
    ficha = cliente.get("/requisitos/A.6.2.2").text
    assert f'id="A.6.2.2.a-{asistente}"' in ficha and f'id="A.6.2.2.a-{chat}"' not in ficha
    assert cliente.post(linea("A.6.2.2", "A.6.2.2.a", chat)).status_code == 400


def test_sin_producto_la_ficha_lo_dice(cliente):
    añadir(cliente, "ChatGPT", "herramienta")
    ficha = cliente.get("/requisitos/A.6.2.2").text
    assert "No hay IA del producto en el" in ficha and "100<small>%</small>" in ficha


def test_las_lineas_apoyadas_no_se_marcan_a_mano(cliente):
    chat = añadir(cliente, "ChatGPT", "herramienta")
    assert cliente.post(linea("A.9.4", "A.9.4.b", chat)).status_code == 400
    assert "Se marcará solo cuando, para este sistema, esté completo: 7.3." in cliente.get("/requisitos/A.9.4").text


def test_subir_y_quitar_un_archivo_de_una_linea(cliente):
    chat = añadir(cliente, "ChatGPT", "herramienta")
    r = cliente.post(linea("A.5.4", "A.5.4.a", chat, "archivos"),
                     files=[("archivos", ("evaluacion chat.pdf", b"%PDF", "application/pdf"))])
    assert "evaluacion chat.pdf" in r.text
    assert cliente.get(linea("A.5.4", "A.5.4.a", chat, "archivos/evaluacion chat.pdf")).content == b"%PDF"
    r = cliente.post(linea("A.5.4", "A.5.4.a", chat, "archivos/evaluacion chat.pdf/quitar"))
    assert "Se ha movido a versiones anteriores como «A.5.4.a - ChatGPT - 2026-03-15 - evaluacion chat.pdf»" in r.text


def test_retirar_quita_sus_lineas_y_manda_sus_archivos_al_historial(cliente, tmp_path):
    asistente = añadir(cliente, "Asistente", "producto")
    chat = añadir(cliente, "ChatGPT", "herramienta")
    cliente.post(linea("A.5.4", "A.5.4.a", asistente))
    cliente.post(linea("A.5.4", "A.5.4.a", chat, "archivos"),
                 files=[("archivos", ("evaluacion.pdf", b"%PDF", "application/pdf"))])
    cliente.post(f"/inventario/{chat}/retirar")
    ficha = cliente.get("/requisitos/A.5.4").text
    assert f'id="A.5.4.a-{chat}"' not in ficha and "100<small>%</small>" in ficha
    assert 'data-nombre="A.5.4.a - ChatGPT - 2026-03-15 - evaluacion.pdf"' in ficha  # en el historial
    base = tmp_path / "general" / "pruebas" / "A.5.4" / "A.5.4.a"
    assert not (base / "ChatGPT").exists()
    cliente.post(f"/inventario/{chat}/activar")
    assert (base / "ChatGPT").is_dir()


def test_renombrar_un_sistema_renombra_sus_carpetas(cliente, tmp_path):
    chat = añadir(cliente, "ChatGPT", "herramienta")
    cliente.post(f"/inventario/{chat}", data={"nombre": "ChatGPT Team", "tipo": "herramienta"})
    base = tmp_path / "general" / "pruebas" / "A.5.4" / "A.5.4.a"
    assert (base / "ChatGPT Team").is_dir() and not (base / "ChatGPT").exists()


def test_reabrir_tambien_desmarca_las_lineas(cliente):
    chat = añadir(cliente, "ChatGPT", "herramienta")
    cliente.post(linea("A.5.4", "A.5.4.a", chat))
    assert 'data-confirmar="/requisitos/A.5.4/reabrir"' in cliente.get("/requisitos/A.5.4").text
    cliente.post("/requisitos/A.5.4/reabrir")
    assert "0 de 1 sistema" in cliente.get("/requisitos/A.5.4").text


def test_vencimientos_por_linea_en_el_panel_y_en_ajustes(cliente, reloj):
    chat = añadir(cliente, "ChatGPT", "herramienta")
    reloj.dia = date(2025, 3, 20)  # marcada hace un año: vence en 5 días (la fecha ya no se cambia a mano)
    cliente.post(linea("8.4", "8.4.a", chat))
    reloj.dia = date(2026, 3, 15)
    ajustes = cliente.get("/ajustes").text
    assert f'id="fecha-8.4.a-{chat}"' in ajustes and "Vence el 20/03/2026" in ajustes
    inicio = cliente.get("/").text  # en «Lo siguiente»
    assert "Vence 20 mar" in inicio and "8.4.a</span> · ChatGPT ·" in inicio
    reloj.dia = date(2026, 3, 25)
    assert "Venció el 20/03/2026" in cliente.get("/").text
    cliente.post(linea("8.4", "8.4.a", chat, "renovar"))
    assert "Vence el 25/03/2027" in cliente.get("/requisitos/8.4").text



def test_subir_version_nueva_en_una_linea(cliente):
    # A.5.4 es «por evento»: la línea no vence, y el botón no habla de renovar
    chat = añadir(cliente, "ChatGPT", "herramienta")
    cliente.post(linea("A.5.4", "A.5.4.a", chat))
    cliente.post(linea("A.5.4", "A.5.4.a", chat, "archivos"), files=[("archivos", ("v1.pdf", b"1", "application/pdf"))])
    ficha = cliente.get("/requisitos/A.5.4").text
    assert "Subir versión nueva" in ficha and "Subir versión nueva y renovar" not in ficha
    assert "revisado el 15/03/2026" in ficha
    cliente.post(linea("A.5.4", "A.5.4.a", chat, "version"), files=[("archivos", ("v2.pdf", b"2", "application/pdf"))])
    ficha = cliente.get("/requisitos/A.5.4").text
    assert "/archivos/v2.pdf" in ficha and 'data-nombre="A.5.4.a - ChatGPT - 2026-03-15 - v1.pdf"' in ficha
