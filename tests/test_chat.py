# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El chat. Ninguna prueba llama a Claude."""
import json
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import chat, db, ia
from portal import guia as guia_portal
from portal.main import crear_app
from conftest import entrar, preparar_cuentas

DIA = date(2026, 3, 15)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def app(bd):
    return crear_app(preparar_cuentas(bd.parent.parent), hoy=lambda: DIA)


@pytest.fixture
def cliente(app):
    with TestClient(app) as c:
        yield entrar(c)


def eventos(texto: str) -> list[dict]:
    return [json.loads(l[6:]) for l in texto.split("\n\n") if l.startswith("data: ")]


# --- Piezas: lo que sabe siempre ---

def test_las_instrucciones_llevan_el_indice_de_la_guia_y_del_manual():
    ins = chat.instrucciones()
    assert ins.count("\n- ") >= 65 + 21
    assert "- 7.2 Competencia: Asegurar que quien trabaja" in ins
    assert "- 5.1 Liderazgo y compromiso: " in ins and "(se apoya en " in ins
    assert "[control del Anexo A]" in ins and "**archivos**" in ins
    assert "[7.2](/requisitos/7.2)" in ins          # cómo enlazar


def test_cada_pantalla_del_indice_del_manual_existe():
    secciones = chat.secciones_manual()
    claves = re.findall(r"^- \*\*([\w-]+)\*\*", chat.indice_manual(), flags=re.M)
    assert len(claves) == 23 and set(claves) == set(secciones)
    assert "Subir versión nueva" in secciones["archivos"]


def test_el_detalle_de_un_requisito_lleva_sus_puntos_y_te_pediran():
    d = chat.detalle_requisito("7.2")
    assert "7.2.a" in d and "7.2.c" in d and "Te pedirán:" in d
    assert "Se apoya en: 5.2" in chat.detalle_requisito("7.3")
    assert "¿Aplica a tu empresa?" in chat.detalle_requisito("A.7.2")
    assert "No hay ningún requisito «9.9»" in chat.detalle_requisito("9.9")


# --- Piezas: Claude va aislado, con solo nuestras herramientas ---

def test_opciones_del_chat(app):
    o = chat.opciones(app.state.consultas_de("general"))
    assert o.model == "claude-opus-5-5" and o.effort == "low"
    assert o.tools == [] and o.setting_sources == [] and o.strict_mcp_config
    assert list(o.mcp_servers) == ["portal"] and o.include_partial_messages
    assert sorted(o.allowed_tools) == sorted(f"mcp__portal__{n}" for n in chat.QUE_CONSULTA)
    assert o.system_prompt["type"] == "file"


# --- Piezas: lo que consulta del espacio, solo lectura ---

def test_el_estado_de_un_requisito(app):
    with TestClient(app) as c:
        entrar(c)
        c.post("/requisitos/7.2/puntos/7.2.a/marcar")
        c.post("/requisitos/7.2/puntos/7.2.a/archivos", files=[("archivos", ("matriz.xlsx", b"x", "application/octet-stream"))])
        c.post("/requisitos/7.2/nota", data={"texto": "La lleva RR. HH."})
        texto = app.state.consultas_de("general").estado_requisito("7.2")
    assert "7.2 Competencia: 1 de 3 puntos" in texto
    assert "- 7.2.a: cumplido (vence el 15/03/2027) · archivos: matriz.xlsx" in texto
    assert "- 7.2.b: pendiente · archivos: ninguno" in texto and "La lleva RR. HH." in texto
    assert "se cumple solo con 5.2" in app.state.consultas_de("general").estado_requisito("7.3")


def test_lo_siguiente_el_inventario_la_declaracion_y_el_cuestionario(app):
    with TestClient(app) as c:
        entrar(c)
        c.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
        c.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
        c.post("/declaracion/cuestionario/entrena", data={"valor": "no"})
        q = app.state.consultas_de("general")
        assert "Hoy es 15/03/2026" in q.lo_siguiente() and "Controles sin decidir: 37" in q.lo_siguiente()
        assert "- ChatGPT (Herramienta de uso)" in q.inventario()
        assert "- A.10.4 Clientes: no aplica · Sin clientes con IA." in q.declaracion()
        assert "¿Entrenáis o ajustáis modelos con datos vuestros? → No" in q.cuestionario()


# --- Recorridos: el panel y la conversación, con un Claude de mentira ---

def test_el_panel_esta_en_las_dos_bases(cliente):
    html = cliente.get("/requisitos/7.2").text
    assert 'data-chat-abrir' in html and '<aside id="chat" class="chat-panel" hidden' in html
    assert "/static/chat.js?v=" in html


def test_preguntar_responde_a_trozos_con_la_pagina(cliente, monkeypatch):
    recibido = []

    async def de_mentira(self, pregunta, pagina):
        recibido.append((pregunta, pagina))
        yield {"consulta": "Leyendo la guía"}
        yield {"texto": "Para la [7.2](/requisitos/7.2) "}
        yield {"texto": "te pedirán certificados."}

    monkeypatch.setattr(chat.Conversacion, "preguntar", de_mentira)
    r = cliente.post("/chat", data={"pregunta": "¿Qué me pedirán?", "pagina": "7.2 Competencia (/requisitos/7.2)"})
    assert r.headers["content-type"].startswith("text/event-stream")
    ev = eventos(r.text)
    assert ev[0].keys() == {"id"} and ev[-1] == {"fin": True}
    assert "".join(e.get("texto", "") for e in ev) == "Para la [7.2](/requisitos/7.2) te pedirán certificados."
    assert {"consulta": "Leyendo la guía"} in ev
    assert recibido == [("¿Qué me pedirán?", "7.2 Competencia (/requisitos/7.2)")]
    # La misma conversación sigue con su id; «Nueva» la cierra y la olvida
    id_ = ev[0]["id"]
    assert eventos(cliente.post("/chat", data={"id": id_, "pregunta": "¿Y la 7.3?"}).text)[0] == {"id": id_}
    assert cliente.post(f"/chat/{id_}/parar").status_code == 204
    assert cliente.post(f"/chat/{id_}/cerrar").status_code == 204
    assert eventos(cliente.post("/chat", data={"id": id_, "pregunta": "Hola"}).text)[0]["id"] != id_


def test_sin_pregunta_lo_dice(cliente):
    ev = eventos(cliente.post("/chat", data={"pregunta": "  "}).text)
    assert {"error": "Escribe la pregunta."} in ev and ev[-1] == {"fin": True}


def test_sin_claude_code_lo_dice_y_no_rompe_nada(cliente, monkeypatch):
    monkeypatch.setattr(ia, "disponible", lambda: False)
    ev = eventos(cliente.post("/chat", data={"pregunta": "Hola"}).text)
    assert any("no se encuentra Claude Code" in e.get("error", "") for e in ev) and ev[-1] == {"fin": True}
    assert cliente.get("/").status_code == 200
