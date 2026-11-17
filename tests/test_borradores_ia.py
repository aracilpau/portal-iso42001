# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los borradores los redacta la IA sobre una estructura fija. Con un Claude de
mentira: ninguna prueba llama al de verdad."""
import io
from datetime import date

import pytest
from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from conftest import en_portal
from portal import borradores, db, ia, word
from portal import guia as guia_portal

DIA = date(2026, 10, 7)
HX = {"HX-Request": "true"}
MARCA = "# BORRADOR BASE (la estructura fija)\n"


class ClaudeDeMentira:
    """Sustituye a ia.tarea: redacta el borrador con los mismos títulos del base (o se los salta) y apunta lo que se le
    da. `preguntas`: lo que dirá que le falta saber."""

    def __init__(self):
        self.mensajes, self.falla, self.rompe = [], "", False
        self.preguntas = ["¿Quién aprueba la política?", "¿Cada cuánto se revisa?"]

    async def __call__(self, nombre, instrucciones, mensaje, esfuerzo="medium", imagenes=None):
        self.mensajes.append(mensaje)
        if self.falla:
            raise ia.ClaudeNoDisponible(self.falla)
        base = mensaje[mensaje.index(MARCA) + len(MARCA):]
        lineas = []
        for l in base.splitlines():
            if l.startswith("#"):
                if self.rompe and l.startswith("## "):
                    continue  # se salta los apartados
                lineas += [l, "Texto formal redactado por la IA. [A CONFIRMAR: el RGPD aplica]"]
        lineas += [borradores.FALTA] + [f"- {p}" for p in self.preguntas]
        return "\n".join(lineas)


@pytest.fixture
def claude(monkeypatch):
    falso = ClaudeDeMentira()
    monkeypatch.setattr(ia, "tarea", falso)
    monkeypatch.setattr(ia, "disponible", lambda: True)
    return falso


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


def textos(r) -> str:
    doc = Document(io.BytesIO(r.content))
    return "\n".join(p.text for p in doc.paragraphs) + "\n".join(c.text for t in doc.tables for f in t.rows for c in f.cells)


# --- Piezas: qué se le da a Claude ---

def test_le_llega_todo_lo_de_la_empresa_pero_nunca_los_archivos(cliente, claude, bd):
    cliente.post("/empresa/respuesta/nombre", data={"valor": "Ejemplo, S.L."})
    cliente.post("/empresa/respuesta/uso", data={"valor": "Un asistente para huéspedes."})
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    cliente.post("/requisitos/5.2/nota", data={"texto": "La aprueba el consejo."})
    cliente.post("/requisitos/5.2/puntos/5.2.a/archivos",
                 files=[("archivos", ("vieja.pdf", b"CONTENIDO SECRETO DEL PDF", "application/pdf"))])
    cliente.post("/requisitos/5.2/borrador")
    m = claude.mensajes[-1]
    assert "Nombre de la empresa: Ejemplo, S.L." in m
    assert "¿Para qué usáis la IA y qué os aporta? Un asistente para huéspedes." in m
    assert "## ChatGPT (herramienta de IA de terceros)" in m and "Para qué sirve y responsable: (sin rellenar)" in m
    assert "- 5.2: La aprueba el consejo." in m
    assert "5.2 Política de IA" in m and "A.2.2" in m  # la política cubre la 5.2 y la A.2.2
    assert "vieja.pdf" not in m and "CONTENIDO SECRETO" not in m
    assert MARCA in m and "# Política de inteligencia artificial de Ejemplo, S.L." in m


def test_la_estructura_se_comprueba():
    b = borradores.Base("x", "# Título\n\n## Uno\nalgo\n## Dos\n", "x.docx", "", [])
    texto, preguntas = borradores.leer("# Título\nhola\n## Uno\nA\n## Dos\nB\n## Lo que falta saber\n- ¿Quién?\n- Otra", b)
    assert preguntas == ["¿Quién?", "Otra"] and texto.startswith("# Título")
    assert borradores.leer("```markdown\n# Título\n## Uno\n## Dos\n## Lo que falta saber\n- Nada.\n```", b)[1] == []
    for mala in ("# Título\n## Uno\n## Lo que falta saber\n- x",            # falta un apartado
                 "# Título\n## Dos\n## Uno\n## Lo que falta saber\n- x",    # cambiados de orden
                 "# Título\n## Uno\n## Dos\n## Tres\n## Lo que falta saber",  # uno de más
                 "# Título\n## Uno\n## Dos\n"):                               # sin «Lo que falta saber»
        with pytest.raises(borradores.EstructuraRota):
            borradores.leer(mala, b)


def test_se_le_pide_que_no_cuente_lo_que_falta_en_el_documento():
    assert "nada de «actualmente no se hace…»" in borradores.INSTRUCCIONES
    assert "Tampoco escribas que ya existe" in borradores.INSTRUCCIONES


def test_se_le_pide_avisar_de_comprobar_los_documentos_que_menciona():
    assert "comprobar que «ese documento» está subido y que esto encaja con él" in borradores.INSTRUCCIONES


def test_se_le_pide_que_no_repita_el_formulario():
    assert "No preguntes nada de lo\n  que ya aparece en «La empresa» o en «Inventario de IA»" in borradores.INSTRUCCIONES


def test_las_preguntas_del_formulario_se_quitan_de_las_suyas_y_del_documento():
    b = borradores.Base("x", "# Título\n## Uno\n", "x.docx", "", [])
    cerrada, abierta = guia_portal.PREGUNTAS[0].texto, guia_portal.ABIERTAS[0].texto
    texto, preguntas = borradores.leer(
        f"# Título\n## Uno\nA\n## Lo que falta saber\n- {cerrada}\n- ¿Dónde se guardará?\n-  {abierta.upper()}.", b)
    assert preguntas == ["¿Dónde se guardará?"]
    assert cerrada not in texto and abierta.upper() not in texto and "- ¿Dónde se guardará?" in texto
    # Si solo preguntaba lo del formulario, no falta nada más: el apartado no se queda vacío
    texto, preguntas = borradores.leer(f"# Título\n## Uno\nA\n## Lo que falta saber\n- {cerrada}", b)
    assert preguntas == [] and texto.endswith("## Lo que falta saber\n- Nada.")


def test_la_huella_cambia_si_cambia_lo_que_se_le_da():
    assert borradores.huella("a") == borradores.huella("a") != borradores.huella("b")


def test_a_confirmar_sale_en_amarillo_como_por_completar():
    doc = Document(io.BytesIO(word.documento("Ley: [A CONFIRMAR: RGPD]. Firma: [POR COMPLETAR: quién]")))
    amarillos = [r.text for r in doc.paragraphs[0].runs if r.font.highlight_color == WD_COLOR_INDEX.YELLOW]
    assert amarillos == ["[A CONFIRMAR: RGPD]", "[POR COMPLETAR: quién]"]


# --- Recorridos: «Hacer borrador» ---

def test_con_ia_sale_el_texto_de_claude_con_su_aviso(cliente, claude):
    r = cliente.post("/requisitos/5.2/borrador")
    assert r.status_code == 200
    t = textos(r)
    assert t.startswith(borradores.AVISO_IA) and "Texto formal redactado por la IA." in t
    assert "Lo que falta saber" in t and "¿Quién aprueba la política?" in t
    assert "borrador del documento hecho con IA" in cliente.get("/actividad").text


def test_si_se_salta_la_estructura_sale_el_de_siempre_con_aviso(cliente, claude):
    claude.rompe = True
    t = textos(cliente.post("/requisitos/5.2/borrador"))
    assert "Hecho sin IA: la IA no ha respetado la estructura del documento." in t
    assert "Texto formal redactado por la IA." not in t and "Política de inteligencia artificial" in t
    assert "borrador del documento descargado (sin IA)" in cliente.get("/actividad").text


def test_sin_claude_sale_el_de_siempre_con_aviso(cliente):
    t = textos(cliente.post("/requisitos/7.4/borrador"))  # una genérica
    assert t.startswith("Hecho sin IA: Claude no está disponible en este ordenador.")
    assert "Base para empezar a escribir" in t and "7.4.a" in t


def test_si_claude_falla_sale_el_de_siempre_con_el_motivo(cliente, claude):
    claude.falla = "Claude está tardando demasiado. Vuelve a probar en un momento."
    t = textos(cliente.post("/requisitos/5.2/borrador"))
    assert t.startswith("Hecho sin IA: Claude está tardando demasiado.")


def test_sin_cambios_no_vuelve_a_llamar_a_claude(cliente, claude):
    primero = textos(cliente.post("/requisitos/5.2/borrador"))
    assert textos(cliente.post("/requisitos/A.2.2/borrador")) == primero  # el mismo documento, desde la A.2.2
    assert len(claude.mensajes) == 1
    cliente.post("/empresa/respuesta/uso", data={"valor": "Algo nuevo."})
    cliente.post("/requisitos/5.2/borrador")
    assert len(claude.mensajes) == 2  # ha cambiado algo de lo que se le da


# --- Recorrido: las preguntas de la IA, en «Empresa» ---

def test_las_preguntas_de_la_ia_salen_en_empresa_y_contestadas_llegan_al_siguiente(cliente, claude, bd):
    cliente.post("/requisitos/5.2/borrador")
    html = cliente.get("/empresa").text
    assert "¿Quién aprueba la política?" in html and "del borrador «politica-ia»" in html
    antes = cliente.get("/empresa").text
    pendientes_antes = int(antes.split(" preguntas contestadas")[0].split(" de ")[-1])
    fila = db.preguntas_ia(bd, 1)[0]
    r = cliente.post(f"/empresa/pregunta-ia/{fila['id']}", data={"valor": "El consejo de administración."}, headers=HX)
    assert "Guardado a las" in r.text
    assert f">El consejo de administración.</textarea>" in cliente.get("/empresa").text
    assert int(cliente.get("/empresa").text.split(" preguntas contestadas")[0].split(" de ")[-1]) == pendientes_antes
    # Otro borrador ya la usa, y a ese le pregunta otra cosa: no se repiten ni se pierden las contestadas
    claude.preguntas = ["¿Quién aprueba la política?", "¿Tenéis comité?"]
    cliente.post("/requisitos/4.3/borrador")
    assert "¿Quién aprueba la política? El consejo de administración." in claude.mensajes[-1]
    textos_ia = [f["texto"] for f in db.preguntas_ia(bd, 1)]
    assert textos_ia.count("¿Quién aprueba la política?") == 1 and "¿Tenéis comité?" in textos_ia
    # Al rehacer el de la política, sus preguntas sin contestar se sustituyen; la contestada se queda
    claude.preguntas = ["¿Dónde se publica?"]
    cliente.post("/empresa/respuesta/uso", data={"valor": "Otra cosa."})
    cliente.post("/requisitos/5.2/borrador")
    textos_ia = [f["texto"] for f in db.preguntas_ia(bd, 1)]
    assert "¿Cada cuánto se revisa?" not in textos_ia and "¿Dónde se publica?" in textos_ia
    assert "¿Quién aprueba la política?" in textos_ia


def test_le_dice_lo_ya_preguntado_para_que_no_lo_repita_con_otras_palabras(cliente, claude):
    cliente.post("/requisitos/5.2/borrador")
    claude.preguntas = ["¿Quién  aprueba la política?", "¿Tenéis comité?"]  # copia una tal cual (con un espacio de más)
    cliente.post("/requisitos/7.4/borrador")
    m = claude.mensajes[-1]
    ya = m[m.index("# Ya preguntado"):m.index(MARCA)]
    assert "- ¿Quién aprueba la política?" in ya and "- ¿Cada cuánto se revisa?" in ya
    html = cliente.get("/empresa").text
    assert html.count("aprueba la política?") == 1 and "¿Tenéis comité?" in html


def test_lo_que_ya_esta_en_el_formulario_no_sale_como_pregunta_de_la_ia(cliente, claude, bd):
    repetida = guia_portal.PREGUNTAS[0].texto
    claude.preguntas = [repetida, "¿Dónde se guardará el documento?"]
    t = textos(cliente.post("/requisitos/5.2/borrador"))
    assert [f["texto"] for f in db.preguntas_ia(bd, 1)] == ["¿Dónde se guardará el documento?"]
    assert "¿Dónde se guardará el documento?" in t and repetida not in t


def test_una_repetida_de_antes_no_se_le_pasa_como_ya_preguntada(cliente, claude, bd):
    # Las que quedaron guardadas antes de este cambio: no hay que invitarle a copiarlas
    repetida = guia_portal.PREGUNTAS[0].texto
    db.poner_preguntas_ia(bd, 1, "otro", [repetida, "¿Tenéis comité?"], DIA)
    cliente.post("/requisitos/5.2/borrador")
    m = claude.mensajes[-1]
    ya = m[m.index("# Ya preguntado"):m.index(MARCA)]
    assert "- ¿Tenéis comité?" in ya and repetida not in ya


def test_una_pregunta_de_otra_empresa_no_existe(cliente):
    assert cliente.post("/empresa/pregunta-ia/999", data={"valor": "x"}).status_code == 404
