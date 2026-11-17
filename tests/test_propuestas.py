# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La ayuda con la Declaración. Ninguna prueba llama a Claude: se usa uno de mentira."""
import json
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import db, guia, ia, propuestas
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 3, 15)
HX = {"HX-Request": "true"}


class ClaudeDeMentira:
    """Sustituye a ia.tarea: apunta lo que se le pregunta y devuelve una respuesta grabada (o falla)."""

    def __init__(self, respuesta="", falla=None):
        self.respuesta, self.falla, self.mensajes = respuesta, falla, []

    async def __call__(self, nombre, instrucciones, mensaje, esfuerzo="medium"):
        self.mensajes.append((nombre, instrucciones, mensaje, esfuerzo))
        if self.falla:
            raise ia.ClaudeNoDisponible(self.falla)
        return self.respuesta


RESPUESTA = """A.2.2 | APLICA | La empresa necesita una política de IA. | aplica casi siempre
A.7.2 | NO APLICA | La empresa no entrena modelos con datos propios. | pregunta 2
A.7.6 | FALTA SABER | ¿Preparáis vosotros los datos con los que trabaja la IA? | pregunta 2
A.10.4 | APLICA | La empresa ofrece IA a sus clientes. | pregunta 4"""


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def claude(monkeypatch):
    falso = ClaudeDeMentira(RESPUESTA)
    monkeypatch.setattr(ia, "tarea", falso)
    monkeypatch.setattr(ia, "disponible", lambda: True)
    return falso


@pytest.fixture
def cliente(bd, claude):
    # Con un sistema en el inventario, los controles en blanco son dudosos y los decide Claude (Declaración mixta).
    # ChatGPT, de tipo herramienta, contesta solo la pregunta 8 (proveedores): A.10.2 y A.10.3 los decide el portal.
    db.crear_sistema(bd, 1, "ChatGPT", "herramienta", DIA)
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


# Las que decide el portal en el cliente de arriba: los 11 de «aplica casi siempre» y los 2 de la pregunta 8
FIJAS = 13


def control(html, codigo):
    i = html.index(f'id="control-{codigo}"')
    return html[i:html.index("</li>", i)]


# --- Piezas: leer la respuesta de Claude ---

def test_lee_una_linea_por_control_con_la_forma_pedida():
    leidas = propuestas.leer(RESPUESTA, propuestas.controles())
    assert set(leidas) == {"A.2.2", "A.7.2", "A.7.6", "A.10.4"}
    assert leidas["A.7.2"].decision == propuestas.NO_APLICA and leidas["A.7.2"].apoyo == "pregunta 2"
    assert leidas["A.7.6"].decision == propuestas.FALTA and leidas["A.7.6"].porque.startswith("¿Preparáis")


def test_lo_que_no_encaja_se_descarta_no_se_adivina():
    texto = """Aquí van mis propuestas:
**A.2.2 | aplica | Política necesaria. | casi siempre**
- A.2.3 | NO APLICA | Sin otras políticas. | pregunta 10
A.2.3 | APLICA | Repetido: vale el primero. | pregunta 10
A.9.9 | APLICA | No existe. | nada
4.1 | APLICA | No es un control. | nada
A.3.2 | QUIZÁ | Decisión rara. | nada
A.3.3 | APLICA |  | sin porqué"""
    leidas = propuestas.leer(texto, propuestas.controles())
    assert set(leidas) == {"A.2.2", "A.2.3"}
    assert leidas["A.2.2"].decision == propuestas.APLICA and leidas["A.2.3"].decision == propuestas.NO_APLICA


def test_lee_el_aviso_si_lo_hay():
    leidas = propuestas.leer("A.4.4 | APLICA | La empresa integra IA. | pregunta 1 | El inventario no tiene IA del producto.\n"
                             "A.7.2 | NO APLICA | No entrena modelos. | pregunta 2 |\n"
                             "A.7.6 | APLICA | Prepara datos. | pregunta 2", propuestas.controles())
    assert leidas["A.4.4"].aviso == "El inventario no tiene IA del producto." and leidas["A.4.4"].apoyo == "pregunta 1"
    assert leidas["A.7.2"].aviso == "" and leidas["A.7.6"].aviso == "" and leidas["A.7.6"].apoyo == "pregunta 2"


def test_solo_vale_un_control_que_se_le_pidio():
    assert propuestas.leer(RESPUESTA, ["A.7.2"]).keys() == {"A.7.2"}


def test_el_mensaje_lleva_la_empresa_el_inventario_y_los_controles(bd):
    perfil = {"datos": {"nombre": "Ejemplo, S.L."}, "respuestas": {"entrena": "no", "clientes": "nose"}}
    db.crear_sistema(bd, 1, "ChatGPT", "herramienta", DIA)
    m = propuestas.mensaje(perfil, db.sistemas(bd, 1), ["A.7.2", "A.2.2"])
    assert "Nombre de la empresa: Ejemplo, S.L." in m and "A qué se dedica: Sin contestar" in m
    assert "¿Entrenáis o ajustáis modelos con datos vuestros? → No" in m and "→ No lo sé" in m
    assert "- ChatGPT (herramienta de uso (de terceros))" in m
    assert "A.7.2 Datos para desarrollo y mejora (depende de la pregunta 2)" in m
    assert "A.2.2 Política de IA (aplica casi siempre)" in m
    m = propuestas.mensaje(perfil, [], ["A.7.6"], {"A.7.6": ("¿Preparáis los datos?", "Sí, los limpiamos")})
    assert "(vacío" in m and "Contestó: «Sí, los limpiamos»" in m


def test_el_mensaje_dice_lo_que_ya_esta_decidido_y_lo_que_decide_claude():
    perfil = {"datos": {}, "respuestas": {"entrena": "no"}}
    fijas = propuestas.fijas(perfil, [Sistema()])
    m = propuestas.mensaje(perfil, [], ["A.2.2", "A.7.2", "A.4.4"], fijas_=fijas)
    assert "  - Ya decidido: APLICA (aplica casi siempre)" in m and "  - Ya decidido: NO APLICA (pregunta 2)" in m
    assert m.count("  - Decide tú") == 1                               # A.4.4: sin contestar y con inventario
    assert "AVISO" in propuestas.INSTRUCCIONES and "Ya decidido" in propuestas.INSTRUCCIONES


# --- Piezas: lo que decide el portal, sin IA (Declaración mixta) ---

class Sistema:
    retirado = None


def perfil_con(**respuestas):
    return {"datos": {}, "respuestas": respuestas}


def test_los_que_aplican_casi_siempre_los_decide_el_portal():
    fijas = propuestas.fijas(perfil_con(), [Sistema()])
    for c in ("A.2.2", "A.3.2", "A.9.4"):
        assert fijas[c].decision == propuestas.APLICA and fijas[c].apoyo == "aplica casi siempre"
        assert fijas[c].quien == propuestas.PORTAL


def test_si_aplica_y_no_no_aplica_con_su_pregunta():
    fijas = propuestas.fijas(perfil_con(entrena="si", infraestructura="no"), [Sistema()])
    assert fijas["A.7.2"].decision == fijas["A.7.6"].decision == propuestas.APLICA
    assert fijas["A.7.2"].apoyo == "pregunta 2"
    assert "«¿Entrenáis o ajustáis modelos con datos vuestros?» Sí." in fijas["A.7.2"].porque
    assert fijas["A.4.5"].decision == propuestas.NO_APLICA and fijas["A.4.5"].apoyo == "pregunta 7"


def test_lo_dudoso_con_inventario_lo_decide_claude_y_sin_inventario_falta_saber():
    con_sistemas = propuestas.fijas(perfil_con(entrena="nose"), [Sistema()])
    assert "A.7.2" not in con_sistemas and "A.4.4" not in con_sistemas  # «No lo sé» y sin contestar
    sin_sistemas = propuestas.fijas(perfil_con(entrena="nose"), [])
    f = sin_sistemas["A.7.2"]
    assert f.decision == propuestas.FALTA and f.porque == "¿Entrenáis o ajustáis modelos con datos vuestros?"
    assert f.apoyo == "pregunta 2"
    retirado = Sistema()
    retirado.retirado = DIA
    assert "A.7.2" in propuestas.fijas(perfil_con(entrena="nose"), [retirado])  # un retirado no cuenta


def test_el_control_de_dos_preguntas_aplica_si_cualquiera_es_si():
    def a83(**r):
        return propuestas.fijas(perfil_con(**r), []).get("A.8.3")
    si = a83(clientes="no", personas="si")
    assert si.decision == propuestas.APLICA and si.apoyo == "pregunta 5"
    assert a83(clientes="si", personas="nose").decision == propuestas.APLICA
    no = a83(clientes="no", personas="no")
    assert no.decision == propuestas.NO_APLICA and no.apoyo == "preguntas 4 y 5"
    falta = a83(clientes="no", personas="nose")
    assert falta.decision == propuestas.FALTA and falta.apoyo == "pregunta 5"
    assert propuestas.fijas(perfil_con(clientes="no", personas="nose"), [Sistema()]).get("A.8.3") is None


def test_con_todo_contestado_decide_los_38_y_siempre_igual():
    todo = perfil_con(**{q.clave: ("si" if n % 2 else "no") for n, q in enumerate(guia.PREGUNTAS)})
    una, otra = propuestas.fijas(todo, [Sistema()]), propuestas.fijas(todo, [Sistema()])
    assert len(una) == 38 and una == otra
    assert all(p.decision != propuestas.FALTA for p in una.values())


def test_claude_no_puede_cambiar_lo_que_decide_el_portal():
    fijas = propuestas.fijas(perfil_con(entrena="no"), [Sistema()])
    leidas = propuestas.leer("A.7.2 | APLICA | Entrena modelos. | inventario\n"
                             "A.7.6 | NO APLICA | La empresa no prepara datos para entrenar. | pregunta 2 | Revisad el inventario.\n"
                             "A.4.4 | APLICA | Integra IA en su producto. | inventario", propuestas.controles())
    res = propuestas.combinar(fijas, leidas, propuestas.controles())
    assert res["A.7.2"].decision == propuestas.NO_APLICA and res["A.7.2"].quien == propuestas.PORTAL
    assert res["A.7.2"].aviso == "La IA habría dicho otra cosa: Entrena modelos."
    assert res["A.7.2"].porque.startswith("Según el cuestionario")    # su porqué, no el de Claude
    assert res["A.7.6"].porque == "La empresa no prepara datos para entrenar." and res["A.7.6"].aviso == "Revisad el inventario."
    assert res["A.4.4"].quien == propuestas.IA and res["A.4.4"].decision == propuestas.APLICA
    assert res["A.2.2"].quien == propuestas.PORTAL                     # sin línea de Claude: el porqué sencillo
    assert "A.10.4" not in res                                          # dudoso y sin respuesta de Claude


def test_que_se_ve_segun_quien_ha_decidido():
    assert propuestas.quien_decide("portal", "pregunta 2") == "según tu respuesta a la pregunta 2"
    assert propuestas.quien_decide("portal", "aplica casi siempre") == "aplica casi siempre"
    assert propuestas.quien_decide("ia", "pregunta 2") == "propuesta de la IA"


def test_la_base_de_datos_de_antes_gana_las_columnas_sin_perder_propuestas(tmp_path):
    import sqlite3
    ruta = tmp_path / "vieja.db"
    db.iniciar(ruta)
    con = sqlite3.connect(ruta)
    con.executescript("DROP TABLE propuesta; CREATE TABLE propuesta (espacio_id INTEGER NOT NULL, control TEXT NOT NULL, "
                      "decision TEXT NOT NULL, porque TEXT NOT NULL, apoyo TEXT NOT NULL DEFAULT '', "
                      "contestado TEXT NOT NULL DEFAULT '', creada TEXT NOT NULL DEFAULT (datetime('now')), "
                      "PRIMARY KEY (espacio_id, control));"
                      "INSERT INTO propuesta (espacio_id, control, decision, porque) VALUES (1, 'A.7.2', 'aplica', 'Vieja.');")
    con.close()
    db.iniciar(ruta)
    p = db.propuestas(ruta, 1)["A.7.2"]
    assert p["porque"] == "Vieja." and p["quien"] == "ia" and p["aviso"] == ""


# --- Piezas: la conexión con Claude ---

def test_claude_va_aislado_con_opus_y_sin_guardar_la_conversacion(tmp_path):
    a = ia.argumentos(tmp_path / "instrucciones.txt", "medium")
    assert a[a.index("--model") + 1] == "claude-opus-5-5" and a[a.index("--effort") + 1] == "medium"
    assert a[a.index("--tools") + 1] == "" and a[a.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in a and "--no-session-persistence" in a and "-p" in a
    assert a[a.index("--system-prompt-file") + 1].endswith("instrucciones.txt")


def test_sin_clave_de_api_en_el_entorno(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-de-mentira")
    assert "ANTHROPIC_API_KEY" not in ia.entorno()


def test_lee_la_respuesta_de_claude_code_y_sus_fallos():
    assert ia.leer_respuesta(json.dumps({"result": " Hola ", "is_error": False})) == "Hola"
    for salida in ("no es json", json.dumps({"is_error": True, "result": "x"}), json.dumps({"result": ""})):
        with pytest.raises(ia.ClaudeNoDisponible):
            ia.leer_respuesta(salida)


def test_sin_claude_code_lo_dice(monkeypatch):
    import asyncio
    monkeypatch.setattr(ia, "programa", lambda: None)
    with pytest.raises(ia.ClaudeNoDisponible, match="no se encuentra Claude Code"):
        asyncio.run(ia.tarea("x", "y", "z"))


# --- Recorridos ---

def test_proponer_deja_cada_propuesta_en_su_control(cliente, claude, bd):
    r = cliente.post("/declaracion/proponer", headers=HX)
    nombre, _, mensaje, esfuerzo = claude.mensajes[-1]
    assert nombre == "declaracion" and esfuerzo == "medium" and mensaje.count("\n- A.") == 38
    assert mensaje.count("Ya decidido:") == FIJAS and mensaje.count("Decide tú") == 38 - FIJAS
    assert "Propuesta de la IA" in control(r.text, "A.7.2") and "pregunta 2" in control(r.text, "A.7.2")
    assert "Falta saber" in control(r.text, "A.7.6") and 'action="/declaracion/propuesta/A.7.6/contestar"' in r.text
    a22 = control(r.text, "A.2.2")
    assert "Aplica casi siempre" in a22 and "La empresa necesita una política de IA." in a22  # el porqué de Claude
    assert "Según tu respuesta a la pregunta 8" in control(r.text, "A.10.2")
    assert "Propuesta de la IA" not in control(r.text, "A.4.4")       # dudoso y Claude no dijo nada: sin propuesta
    assert f"Claude no ha propuesto nada para {38 - FIJAS - 3} controles" in r.text
    assert f"Aceptar todas ({FIJAS + 2})" in r.text                    # las del portal, A.7.2 y A.10.4; no la de falta saber
    assert not db.decisiones(bd, 1)                                    # proponer no decide nada
    assert "propuestas de la IA para la Declaración" in cliente.get("/actividad").text


def test_aceptar_una_la_decide_como_a_mano(cliente, bd):
    cliente.post("/declaracion/proponer", headers=HX)
    r = cliente.post("/declaracion/propuesta/A.7.2/aceptar", headers=HX)
    d = db.decisiones(bd, 1)["A.7.2"]
    assert d.aplica is False and d.porque == "La empresa no entrena modelos con datos propios."
    assert "Propuesta de la IA" not in control(r.text, "A.7.2")
    assert "La empresa no entrena modelos con datos propios. (propuesta de la IA)" in cliente.get("/actividad").text
    cliente.post("/declaracion/propuesta/A.10.2/aceptar", headers=HX)
    assert "(según tu respuesta a la pregunta 8)" in cliente.get("/actividad").text
    assert "La empresa no entrena modelos" in cliente.get("/declaracion/cambios").text
    assert cliente.post("/declaracion/propuesta/A.7.6/aceptar").status_code == 400  # falta saber: no se acepta


def test_aceptar_todas_respeta_lo_decidido_y_lo_que_falta_saber(cliente, bd):
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    cliente.post("/declaracion/proponer", headers=HX)
    r = cliente.post("/declaracion/propuestas/aceptar-todas", headers=HX)
    decs = db.decisiones(bd, 1)
    assert decs["A.2.2"].aplica is True and decs["A.7.2"].aplica is False
    assert "A.7.6" not in decs                                        # falta saber
    assert decs["A.10.4"].aplica is False                             # ya decidido: no se toca
    otra = control(r.text, "A.10.4")
    assert "La IA propondría otra cosa" in otra and "Cambiar a «Aplica»" in otra


def test_en_un_control_decidido_que_coincide_no_dice_nada(cliente):
    cliente.post("/declaracion/A.2.2", data={"aplica": "si", "porque": "Tenemos política."})
    cliente.post("/declaracion/proponer", headers=HX)
    assert "propuesta-" not in control(cliente.get("/declaracion").text, "A.2.2")


def test_descartar_y_decidir_a_mano_quitan_la_propuesta(cliente, bd):
    cliente.post("/declaracion/proponer", headers=HX)
    cliente.post("/declaracion/propuesta/A.2.2/descartar", headers=HX)
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    quedan = set(db.propuestas(bd, 1))
    assert "A.2.2" not in quedan and "A.10.4" not in quedan and {"A.7.2", "A.7.6"} <= quedan


def test_contestar_lo_que_falta_vuelve_a_proponer_ese_control(cliente, claude, bd):
    cliente.post("/declaracion/proponer", headers=HX)
    claude.respuesta = "A.7.6 | APLICA | La empresa limpia y prepara los datos que usa su IA. | respuesta de la empresa"
    r = cliente.post("/declaracion/propuesta/A.7.6/contestar", data={"texto": "Sí, los limpiamos"}, headers=HX)
    _, _, mensaje, _ = claude.mensajes[-1]
    assert mensaje.count("\n- A.") == 1 and "Contestó: «Sí, los limpiamos»" in mensaje
    p = db.propuestas(bd, 1)["A.7.6"]
    assert p["decision"] == "aplica" and p["contestado"] == "Sí, los limpiamos"
    assert "Propuesta de la IA" in control(r.text, "A.7.6")


def test_si_claude_no_esta_propone_lo_del_portal_y_deja_lo_demas(cliente, claude, bd):
    cliente.post("/declaracion/proponer", headers=HX)
    claude.falla = "Claude no está disponible: no se encuentra Claude Code en este ordenador."
    r = cliente.post("/declaracion/proponer", headers=HX)
    assert "no se encuentra Claude Code" in r.text and f"Se han propuesto los {FIJAS} controles" in r.text
    quedan = db.propuestas(bd, 1)
    assert len(quedan) == FIJAS + 3 and quedan["A.7.2"]["quien"] == "ia"   # lo de Claude de antes se queda
    assert quedan["A.2.2"]["porque"] != "La empresa necesita una política de IA."  # el porqué sencillo del portal


def test_si_responde_sin_la_forma_pedida_lo_dice_y_propone_lo_del_portal(cliente, claude, bd):
    claude.respuesta = "Creo que la mayoría aplican, pero depende."
    r = cliente.post("/declaracion/proponer", headers=HX)
    assert "no con la forma esperada" in r.text
    quedan = db.propuestas(bd, 1)
    assert len(quedan) == FIJAS and all(p["quien"] == "portal" for p in quedan.values())


def test_sin_claude_code_se_puede_proponer_lo_que_decide_el_portal(bd, claude, monkeypatch):
    monkeypatch.setattr(ia, "disponible", lambda: False)
    with en_portal(bd, hoy=lambda: DIA) as c:
        html = c.get("/declaracion").text
        assert re.search(r'<button class="boton boton-acento" type="submit">\s*<span class="sin-pensar">Proponer qué controles aplican<', html)
        assert "se proponen los controles que se deciden con tus respuestas" in html
        c.post("/declaracion/cuestionario/entrena", data={"valor": "no"}, headers=HX)
        r = c.post("/declaracion/proponer", headers=HX)
    assert not claude.mensajes                                          # ni se intenta
    assert "Según tu respuesta a la pregunta 2" in control(r.text, "A.7.2")
    assert len(db.propuestas(bd, 1)) == 38                              # sin inventario, el portal los decide todos


def test_el_aviso_se_ve_en_el_control(cliente, claude):
    claude.respuesta = "A.4.4 | APLICA | La empresa integra IA. | inventario | Dice que no desarrolla IA, pero tiene IA del producto."
    r = cliente.post("/declaracion/proponer", headers=HX)
    assert "Míralo:</strong> Dice que no desarrolla IA, pero tiene IA del producto." in control(r.text, "A.4.4")
