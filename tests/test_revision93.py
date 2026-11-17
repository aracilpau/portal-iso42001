# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El borrador de la revisión por la dirección (9.3). Ninguna prueba llama a Claude."""
import io
import re
from datetime import date

import pytest
from docx import Document
from fastapi.testclient import TestClient

from portal import db, ia, revision93
from portal.main import crear_app
from conftest import en_portal, entrar


class Reloj:
    def __init__(self, dia):
        self.dia = dia

    def __call__(self):
        return self.dia


class ClaudeDeMentira:
    def __init__(self, respuesta="", falla=None):
        self.respuesta, self.falla, self.mensajes = respuesta, falla, []

    async def __call__(self, nombre, instrucciones, mensaje, esfuerzo="medium", imagenes=None):
        self.mensajes.append((nombre, mensaje, esfuerzo))
        if self.falla:
            raise ia.ClaudeNoDisponible(self.falla)
        return self.respuesta


ACTA = """# Revisión por la dirección del sistema de gestión de la IA
Ejemplo, S.L. revisa su sistema de gestión de la IA del 15/03/2026 al 15/09/2026.
## Datos de la reunión
- Fecha: [POR COMPLETAR: fecha de la reunión]
- Asistentes: [POR COMPLETAR: asistentes]
## 1. Acciones de revisiones anteriores
No consta ninguna revisión anterior en el portal.
## 2. Cambios en el contexto y en las partes interesadas
Se incorporó una persona nueva.
## 3. Desempeño del sistema de gestión de la IA
Los requisitos obligatorios están al 4 %.
## 4. Oportunidades de mejora
- Completar la política de IA (5.2).
## 5. Conclusiones y decisiones de la dirección
[POR COMPLETAR: decisiones con responsable y plazo]"""


@pytest.fixture
def reloj():
    return Reloj(date(2026, 3, 15))


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def claude(monkeypatch):
    falso = ClaudeDeMentira(ACTA)
    monkeypatch.setattr(ia, "tarea", falso)
    monkeypatch.setattr(ia, "disponible", lambda: True)
    return falso


@pytest.fixture
def cliente(bd, reloj, claude):
    with en_portal(bd, hoy=reloj) as c:
        yield c


# --- Piezas ---

def test_el_periodo_es_desde_la_ultima_revision_subida_a_la_9_3_o_el_ultimo_año():
    hoy = date(2026, 10, 7)
    assert revision93.periodo([], hoy) == (date(2025, 10, 7), hoy, False)
    actividad = [{"requisito": "9.3", "accion": "subido", "cuando": "2026-02-10T10:00:00"},
                 {"requisito": "9.3", "accion": "version", "cuando": "2026-05-20T10:00:00"},
                 {"requisito": "9.2", "accion": "subido", "cuando": "2026-09-01T10:00:00"},   # de otro requisito
                 {"requisito": "9.3", "accion": "marcado", "cuando": "2026-09-02T10:00:00"}]  # no es subir
    assert revision93.periodo(actividad, hoy) == (date(2026, 5, 20), hoy, True)


def test_valida_la_forma_del_acta():
    assert revision93.valida(ACTA)
    assert not revision93.valida("Aquí va el acta, sin apartados.")
    assert not revision93.valida("# Título\n## Solo uno")


def test_el_word_lleva_el_aviso_los_apartados_y_resalta_lo_que_falta():
    doc = Document(io.BytesIO(revision93.word(ACTA)))
    textos = [p.text for p in doc.paragraphs]
    assert textos[0].startswith("Borrador preparado con IA")
    assert "Revisión por la dirección del sistema de gestión de la IA" in textos
    assert "1. Acciones de revisiones anteriores" in textos and "Completar la política de IA (5.2)." in textos
    resaltados = [r.text for p in doc.paragraphs for r in p.runs if r.font.highlight_color]
    assert "[POR COMPLETAR: fecha de la reunión]" in resaltados and len(resaltados) == 3


# --- Recorridos ---

def test_el_boton_esta_en_el_avance_de_inicio_con_su_periodo(cliente):
    html = cliente.get("/").text
    assert 'action="/revision-direccion" data-descargar' in html
    assert re.search(r"pasado del 15/03/2025 al 15/03/2026\. Es el último año", html)


def test_prepara_el_borrador_con_los_datos_del_periodo(cliente, claude, reloj):
    cliente.post("/declaracion/cuestionario/nombre", data={"valor": "Ejemplo, S.L."})
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    cliente.post("/eventos/persona", data={"requisitos": []})
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    reloj.dia = date(2026, 9, 15)
    r = cliente.post("/revision-direccion")
    assert r.status_code == 200 and r.headers["content-disposition"].startswith("attachment; filename*=UTF-8''")
    assert "Revision%20por%20la%20direccion%202025-09-15%20a%202026-09-15.docx" in r.headers["content-disposition"]
    assert Document(io.BytesIO(r.content)).paragraphs[0].text.startswith("Borrador preparado con IA")
    nombre, datos, esfuerzo = claude.mensajes[-1]
    assert nombre == "revision93" and esfuerzo == "medium"
    assert "# Empresa: Ejemplo, S.L." in datos and "del 15/09/2025 al 15/09/2026" in datos
    assert "Persona nueva o cambio de puesto" in datos                       # el evento
    assert "sistema dado de alta: ChatGPT" in datos                           # el inventario
    assert "A.10.4: sin decidir → no aplica. Motivo: Sin clientes con IA." in datos
    assert "- marcado como cumplido: 1" in datos
    assert "- 9.2 Auditoría interna: sin completar" in datos
    assert "borrador de la revisión por la dirección preparado" in cliente.get("/actividad").text


def test_tras_subir_una_revision_a_la_9_3_el_periodo_empieza_ahi(cliente, reloj):
    reloj.dia = date(2026, 6, 1)
    cliente.post("/requisitos/9.3/puntos/9.3.a/archivos", files=[("archivos", ("acta.pdf", b"%PDF", "application/pdf"))])
    reloj.dia = date(2026, 9, 15)
    assert re.search(r"pasado del 01/06/2026 al 15/09/2026\.", cliente.get("/").text)


def test_si_claude_falla_o_responde_raro_lo_dice(cliente, claude):
    claude.respuesta = "No sé hacer actas."
    r = cliente.post("/revision-direccion")
    assert r.status_code == 502 and "forma esperada" in r.text
    claude.falla = "Claude no está disponible: no se encuentra Claude Code en este ordenador."
    r = cliente.post("/revision-direccion")
    assert r.status_code == 503 and "no se encuentra Claude Code" in r.text
