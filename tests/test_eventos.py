# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El botón «Ha pasado algo» y la pregunta cada 4 meses."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from guia import datos
from portal import db, guia
from portal.db import Marca, Sistema
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.seguimiento import Seguimiento, proxima_pregunta

DIA = date(2026, 3, 15)


def sistema(id, nombre, tipo):
    return Sistema(id, nombre, tipo, **{c: "" for c in db.CAMPOS}, actualizado=DIA, retirado=None)


ASISTENTE = sistema(1, "Asistente", "producto")
CHAT = sistema(2, "ChatGPT", "herramienta")


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    # El espacio se crea el día que simulan las pruebas, no el de hoy de verdad: la pregunta
    # cuenta sus 4 meses desde entonces
    with db.conectar(ruta) as con:
        con.execute("UPDATE espacio SET creado = ?", (DIA.isoformat(),))
    con.close()
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



def lo_siguiente(cliente):
    """La lista «Lo siguiente» de Inicio, donde están los avisos."""
    html = cliente.get("/").text
    return html[html.index('<ol class="tareas"'):html.index('</ol>', html.index('<ol class="tareas"'))]


def tareas(cliente):
    return lo_siguiente(cliente).count('<li class="tarea">')


# --- Piezas: las situaciones de la guía ---

def test_hay_cinco_situaciones_y_todo_lo_por_evento_se_reabre_de_alguna_forma():
    assert [s.clave for s in guia.situaciones()] == ["persona", "proveedor", "incidente", "empresa", "fuera"]
    con_situacion = {r.codigo for s in guia.situaciones() for r in s.requisitos}
    al_dar_de_alta = {r.codigo for r in guia.ALTA.requisitos}
    solos = {r.codigo for r in guia.requisitos() if any(p.por_sistema for p in r.puntos)}
    por_evento = {r.codigo for r in guia.requisitos() if "Por evento" in r.cada_cuanto}
    assert por_evento <= con_situacion | al_dar_de_alta | solos


def test_la_comprobacion_pilla_un_por_evento_que_nada_reabre(monkeypatch):
    sin_persona = [s for s in datos.SITUACIONES if s[0] != "persona"]
    monkeypatch.setattr(datos, "SITUACIONES", sin_persona)
    with pytest.raises(AssertionError, match="7.2 es por evento"):
        datos.comprobar()


def test_al_dar_de_alta_se_pregunta_por_lo_de_toda_la_empresa():
    assert [r.codigo for r in guia.ALTA.requisitos] == ["8.2", "8.3", "A.10.3"]


# --- Piezas: qué se reabre ---

def test_reabrir_un_requisito_coge_lo_marcado_a_mano_y_no_lo_apoyado():
    req = guia.requisito("7.2")
    est = Seguimiento({"7.2.a", "7.2.b"})
    assert sorted(p.codigo for p, x in est.a_reabrir(req)) == ["7.2.a", "7.2.b"]
    assert Seguimiento(set()).a_reabrir(req) == []  # nada marcado: nada que reabrir


def test_en_los_puntos_por_sistema_se_reabren_todas_las_lineas():
    req = guia.requisito("8.4")
    lineas = {("8.4.a", 1): Marca(DIA), ("8.4.a", 2): Marca(DIA)}
    est = Seguimiento(set(), sistemas=[ASISTENTE, CHAT], lineas=lineas)
    assert sorted(x.nombre for p, x in est.a_reabrir(req)) == ["Asistente", "ChatGPT"]


def test_la_pregunta_toca_a_los_4_meses_de_la_ultima_respuesta():
    assert proxima_pregunta(4, DIA, None) == date(2026, 7, 15)
    assert proxima_pregunta(4, DIA, date(2026, 5, 1)) == date(2026, 9, 1)
    assert proxima_pregunta(0, DIA, None) is None  # «Nunca»


# --- Recorridos: el botón ---

def test_elegir_quitar_uno_y_reabrir(cliente):
    for p in ("7.2.a", "7.2.b", "7.3.b"):
        cliente.post(f"/requisitos/{p[:3]}/puntos/{p}/marcar")
    pagina = cliente.get("/eventos/persona").text
    assert 'value="7.2" checked' in pagina and 'value="7.3" checked' in pagina
    assert "No se reabre: revisa lo que toque en la ficha de cada IA" in pagina  # A.4.6 se cumple con el inventario
    assert f'data-info="{guia.requisito("7.2").resumen}"' in pagina  # la mini explicación al pasar el ratón

    r = cliente.post("/eventos/persona", data={"requisitos": ["7.2"]})  # se quita la 7.3
    assert "reabiertos 7.2." in r.text
    ficha_72 = cliente.get("/requisitos/7.2").text
    ficha_73 = cliente.get("/requisitos/7.3").text
    assert "/requisitos/7.2/puntos/7.2.a/marcar" in ficha_72  # vuelve a pendiente: se puede marcar
    assert "/requisitos/7.3/puntos/7.3.b/desmarcar" in ficha_73  # la que se quitó sigue marcada


def test_un_requisito_ya_pendiente_no_se_puede_elegir(cliente):
    pagina = cliente.get("/eventos/proveedor").text
    assert "Nada que volver a revisar: ya está pendiente" in pagina and 'name="requisitos"' not in pagina


def test_una_situacion_que_no_existe(cliente):
    assert cliente.get("/eventos/sistema").status_code == 404  # ya no está en el botón


def test_un_control_que_no_aplica_no_sale(cliente):
    cliente.post("/declaracion/A.10.3", data={"aplica": "no", "porque": "No usamos proveedores de IA."})
    pagina = cliente.get("/eventos/proveedor").text
    assert "A.10.2" in pagina and "A.10.3" not in pagina


def test_inicio_lleva_a_cada_situacion(cliente):
    assert 'href="/eventos/fuera"' in cliente.get("/").text
    assert "Cambio de fuera" in cliente.get("/eventos").text


# --- Recorridos: dar de alta un sistema ---

def test_al_dar_de_alta_pregunta_y_reabre_lo_elegido(cliente):
    cliente.post("/requisitos/8.2/puntos/8.2.a/marcar")
    cliente.post("/requisitos/A.10.3/puntos/A.10.3.a/marcar")
    r = cliente.post("/inventario", data={"nombre": "Claude", "tipo": "herramienta"})
    assert "Has dado de alta «Claude»" in r.text
    assert 'value="8.2" checked' in r.text and 'value="A.10.3" checked' in r.text
    assert "Nada que volver a revisar: ya está pendiente" in r.text  # la 8.3, sin nada marcado

    claude = r.url.path.rsplit("/", 1)[1]
    r = cliente.post(f"/inventario/{claude}/reabrir", data={"requisitos": ["8.2"]})  # se quita A.10.3
    assert "Reabiertos 8.2." in r.text and "Has dado de alta" not in r.text
    assert "/requisitos/8.2/puntos/8.2.a/marcar" in cliente.get("/requisitos/8.2").text
    assert "/requisitos/A.10.3/puntos/A.10.3.a/desmarcar" in cliente.get("/requisitos/A.10.3").text


def test_al_volver_a_activar_tambien_pregunta(cliente):
    r = cliente.post("/inventario", data={"nombre": "GPT", "tipo": "herramienta"})
    gpt = r.url.path.rsplit("/", 1)[1]
    cliente.post(f"/inventario/{gpt}/retirar")
    r = cliente.post(f"/inventario/{gpt}/activar")
    assert "vuelve a estar activo" in r.text  # sin nada que reabrir, a la lista como siempre

    cliente.post(f"/inventario/{gpt}/retirar")
    cliente.post("/requisitos/8.2/puntos/8.2.a/marcar")
    r = cliente.post(f"/inventario/{gpt}/activar")
    assert "Has vuelto a activar «GPT»" in r.text and 'value="8.2" checked' in r.text


def test_sin_nada_que_reabrir_no_pregunta(cliente):
    r = cliente.post("/inventario", data={"nombre": "Claude", "tipo": "herramienta"})
    assert "Has dado de alta" not in r.text and "Sistema nuevo" not in lo_siguiente(cliente)


def test_si_se_sale_sin_contestar_queda_en_los_avisos(cliente):
    cliente.post("/requisitos/8.2/puntos/8.2.a/marcar")
    r = cliente.post("/inventario", data={"nombre": "Claude", "tipo": "herramienta"})
    claude = r.url.path.rsplit("/", 1)[1]
    cliente.get("/")  # se va a otra página sin contestar

    v = lo_siguiente(cliente)
    assert "Sistema nuevo" in v and ">Claude</a>" in v and tareas(cliente) == 1
    assert "Has dado de alta «Claude»" in cliente.get(f"/inventario/{claude}").text  # la ficha sigue preguntando

    cliente.post(f"/inventario/{claude}/no-reabrir")
    assert "Sistema nuevo" not in lo_siguiente(cliente) and tareas(cliente) == 0
    assert "Has dado de alta" not in cliente.get(f"/inventario/{claude}").text
    assert "/requisitos/8.2/puntos/8.2.a/desmarcar" in cliente.get("/requisitos/8.2").text  # nada reabierto


def test_no_hace_falta_desde_la_ficha(cliente):
    cliente.post("/requisitos/8.2/puntos/8.2.a/marcar")
    r = cliente.post("/inventario", data={"nombre": "Claude", "tipo": "herramienta"})
    r = cliente.post(r.url.path + "/no-reabrir")
    assert "No se ha reabierto nada." in r.text and "Has dado de alta" not in r.text


def test_un_sistema_retirado_deja_de_preguntar(cliente):
    cliente.post("/requisitos/8.2/puntos/8.2.a/marcar")
    r = cliente.post("/inventario", data={"nombre": "Claude", "tipo": "herramienta"})
    cliente.post(r.url.path + "/retirar")
    assert "Sistema nuevo" not in lo_siguiente(cliente)


# --- Recorridos: la pregunta en «Lo siguiente» ---

def test_la_pregunta_sale_a_los_4_meses_y_no_nada_la_aplaza(cliente, reloj):
    assert "¿Ha pasado algo?" not in lo_siguiente(cliente)
    reloj.dia = date(2026, 7, 15)
    # A los 4 meses también tocan los 4 recordatorios recomendados de cada 3 meses: 4 + la pregunta
    assert "¿Ha pasado algo?" in lo_siguiente(cliente) and tareas(cliente) == 5

    cliente.post("/avisos/nada")
    assert "¿Ha pasado algo?" not in lo_siguiente(cliente) and tareas(cliente) == 4
    assert "15/11/2026" in cliente.get("/ajustes").text  # la próxima, 4 meses después


def test_reabrir_desde_el_boton_tambien_cuenta_como_respuesta(cliente, reloj):
    reloj.dia = date(2026, 7, 15)
    cliente.post("/eventos/incidente", data={})
    assert "¿Ha pasado algo?" not in lo_siguiente(cliente)


def test_cambiar_cada_cuanto_y_volver_a_lo_recomendado(cliente, reloj):
    cliente.post("/ajustes/preguntar", data={"meses": "0"})
    reloj.dia = date(2027, 3, 15)
    assert "¿Ha pasado algo?" not in lo_siguiente(cliente)  # «Nunca»
    ajustes = cliente.get("/ajustes").text
    assert 'value="0" selected' in ajustes and "Volver a los valores recomendados" in ajustes

    cliente.post("/ajustes/plazos/por-defecto")
    assert 'value="4" selected' in cliente.get("/ajustes").text
    assert cliente.post("/ajustes/preguntar", data={"meses": "5"}).status_code == 400


def test_sin_recordatorios_en_que_avisa_no_pregunta(cliente, reloj):
    cliente.post("/ajustes/avisos", data={"avisar_vencidos": "1", "avisar_pronto": "1"})
    reloj.dia = date(2026, 7, 15)
    assert "¿Ha pasado algo?" not in lo_siguiente(cliente)
