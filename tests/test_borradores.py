# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los borradores de documentos. Sin IA."""
import io
from datetime import date
from urllib.parse import unquote

import pytest
from docx import Document
from fastapi.testclient import TestClient

from portal import borradores, db
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 10, 7)
PERFIL = {"datos": {"nombre": "Ejemplo, S.L.", "actividad": "software de reservas para hoteles"},
          "respuestas": {"desarrolla": "si", "proveedores": "no", "clientes": "nose"}}


class Sistema:
    def __init__(self, nombre, tipo, para_que="", retirado=None):
        self.nombre, self.tipo, self._para_que, self.retirado = nombre, tipo, para_que, retirado

    def campo(self, c):
        return self._para_que if c == "para_que" else ""


SISTEMAS = [Sistema("Asistente de reservas", "producto", "Responde a los huéspedes."), Sistema("ChatGPT", "herramienta"),
            Sistema("Viejo", "herramienta", retirado=date(2026, 1, 1))]


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


# --- Piezas: las plantillas y el relleno ---

def test_las_nueve_plantillas_estan_y_no_tienen_errores():
    assert len(set(borradores.PLANTILLAS.values())) == 9
    assert borradores.comprobar() == []


def test_la_comprobacion_pilla_las_erratas(tmp_path, monkeypatch):
    (tmp_path / "politica-ia.md").write_text("Hola {nombr}\n[si clientez]\nx\n[/si]\n[si datos]\nsin cerrar\n",
                                             encoding="utf-8")
    monkeypatch.setattr(borradores, "CARPETA", tmp_path)
    errores = borradores.comprobar()
    assert "politica-ia: hueco desconocido {nombr}" in errores
    assert "politica-ia: pregunta desconocida «clientez»" in errores
    assert "politica-ia: un apartado [si …] sin cerrar" in errores
    assert any("falta la plantilla alcance.md" in e for e in errores)


def test_los_huecos_se_rellenan_y_lo_que_falta_queda_por_completar():
    texto = borradores.rellenar("{nombre} se dedica a {actividad}. Lo aprueba {direccion}. Hoy: {fecha}.\n\n{sistemas}",
                                PERFIL, SISTEMAS, DIA)
    assert texto.startswith("Ejemplo, S.L. se dedica a software de reservas para hoteles.")
    assert "Lo aprueba [POR COMPLETAR: quién es la dirección que aprueba]." in texto and "Hoy: 07/10/2026." in texto
    assert "- **Asistente de reservas** (IA de nuestro producto): Responde a los huéspedes." in texto
    assert "- **ChatGPT** (herramienta de IA de terceros que usa la plantilla)" in texto and "Viejo" not in texto


def test_sin_inventario_lo_dice():
    assert "[POR COMPLETAR: el inventario de IA del portal está vacío" in borradores.rellenar("{sistemas}", PERFIL, [], DIA)


def test_un_nombre_que_acaba_en_punto_no_deja_dos_puntos():
    assert borradores.rellenar("Es de {nombre}. Fin...", PERFIL, [], DIA) == "Es de Ejemplo, S.L. Fin..."


def test_los_apartados_salen_segun_el_cuestionario():
    plantilla = ("A\n[si desarrolla]\nDesarrollamos.\n[/si]\n[si no desarrolla]\nNo desarrollamos.\n[/si]\n"
                 "[si proveedores]\nProveedores.\n[/si]\n[si no proveedores]\nSin proveedores.\n[/si]\n"
                 "[si clientes]\nClientes.\n[/si]\n[si no clientes]\nSin clientes.\n[/si]\nZ\n")
    texto = borradores.rellenar(plantilla, PERFIL, [], DIA)
    assert "Desarrollamos." in texto and "No desarrollamos." not in texto          # Sí
    assert "Sin proveedores." in texto and "Proveedores.\n" not in texto           # No
    assert "[POR COMPLETAR: confirmad «¿Ofrecéis IA a clientes o a usuarios de fuera?»; si no, quitad esto]\nClientes." in texto
    assert "Sin clientes." not in texto                                            # No lo sé: sale el «sí» con aviso
    assert "[si" not in texto and "[/si]" not in texto


def test_el_aviso_de_no_lo_se_en_una_tabla_va_dentro_de_la_celda():
    plantilla = "| Rol | Persona |\n|---|---|\n| Dirección | X |\n[si clientes]\n| Clientes | Y |\n[/si]\n"
    texto = borradores.rellenar(plantilla, PERFIL, [], DIA)
    assert "| [POR COMPLETAR: confirmad «¿Ofrecéis IA a clientes o a usuarios de fuera?»; si no, quitad esto] Clientes | Y |" in texto


def test_el_word_tiene_tablas_listas_y_resaltados():
    datos, nombre = borradores.documento("A.3.2", PERFIL, SISTEMAS, DIA)
    assert nombre == "Roles y responsabilidades - borrador 2026-10-07.docx"
    doc = Document(io.BytesIO(datos))
    textos = [p.text for p in doc.paragraphs]
    assert textos[0].startswith("Borrador hecho con la plantilla del portal")
    assert "Roles y responsabilidades del sistema de gestión de la IA de Ejemplo, S.L." in textos
    tabla = doc.tables[0]
    assert [c.text for c in tabla.rows[0].cells] == ["Rol", "Qué hace", "Persona"]
    roles = [f.cells[0].text for f in tabla.rows]
    assert "Desarrollo de IA" in roles and "Relación con proveedores de IA" not in roles   # desarrolla Sí, proveedores No
    resaltados = [r.text for p in doc.paragraphs for r in p.runs if r.font.highlight_color]
    assert "[POR COMPLETAR: nombre y puesto]" in resaltados
    # Un párrafo partido en varias líneas en la plantilla sale entero
    assert any(t.startswith("Dice quién es responsable de qué") and t.endswith("aparecen en él.") for t in textos)


def test_cada_plantilla_se_puede_hacer_word():
    for codigo in borradores.PLANTILLAS:
        datos, _ = borradores.documento(codigo, PERFIL, SISTEMAS, DIA)
        assert Document(io.BytesIO(datos)).paragraphs


# --- Piezas: la base genérica ---

def test_la_generica_sale_en_28_requisitos_que_piden_un_documento_propio():
    from portal import guia
    genericas = [r.codigo for r in guia.requisitos() if borradores.con_borrador(r.codigo) and r.codigo not in borradores.PLANTILLAS]
    assert len(genericas) == 28 and "7.4" in genericas and "A.6.2.2" in genericas
    assert not borradores.con_borrador("7.3") and not borradores.con_borrador("8.1") and not borradores.con_borrador("4.4")


def test_la_generica_tiene_un_apartado_por_punto_de_documento_y_lo_demas_aparte():
    from portal import guia
    texto = borradores.generica(guia.requisito("4.1"))
    for punto in ("4.1.a", "4.1.b", "4.1.c"):
        assert f"## {punto} — " in texto
    assert "## 4.1.d" not in texto and "## Lo que no va en este documento" in texto and "**4.1.d**" in texto
    assert "El auditor pedirá: Documento de contexto" in texto and "{nombre}" in texto
    titulo = guia.punto("4.1.a").titulo_llano or guia.punto("4.1.a").texto
    assert texto.count(titulo.rstrip(".")) == 1  # sin repetir el título del punto


def test_la_generica_usa_la_explicacion_en_llano_si_la_hay(monkeypatch):
    from portal import guia
    req = guia.requisito("7.4")
    monkeypatch.setattr(req.puntos[0], "titulo_llano", "Un plan de comunicación")
    monkeypatch.setattr(req.puntos[0], "explicacion", "Una tabla con qué, a quién y cuándo.")
    texto = borradores.generica(req)
    assert "## 7.4.a — Un plan de comunicación" in texto and "[POR COMPLETAR: Una tabla con qué, a quién y cuándo." in texto


def test_la_generica_se_rellena_con_el_nombre_y_se_hace_word():
    datos, nombre = borradores.documento("A.6.2.2", PERFIL, SISTEMAS, DIA)
    textos = " ".join(p.text for p in Document(io.BytesIO(datos)).paragraphs)
    assert nombre.startswith("A.6.2.2 ") and nombre.endswith(" - base 2026-10-07.docx")
    assert "Ejemplo, S.L." in textos and "Base para empezar a escribir" in textos and "[POR COMPLETAR" in textos


# --- Piezas: dónde se sube cada borrador ---

def test_cada_borrador_dice_donde_se_sube_y_que_no_cubre():
    d = borradores.donde("4.1")
    assert d.cubre == ["4.1.a", "4.1.b", "4.1.c", "4.2.a", "4.2.b", "4.2.c"]  # también los de la 4.2: mismo documento
    assert d.aparte == [("4.1.d", "se cumple solo con 9.3: no hace falta subir nada.")]
    politica = borradores.donde("5.2")
    assert politica.firmado == ["5.2.e"] and "A.2.2.b" in politica.cubre
    assert [c for c, _ in politica.aparte] == ["5.2.f"] and "correo" in politica.aparte[0][1]
    assert borradores.donde("10.2").cubre == [] and "procedimiento" in borradores.donde("10.2").nota
    assert borradores.donde("7.4").cubre == ["7.4.a"]  # la genérica, también


def test_todos_los_puntos_de_donde_se_sube_existen_y_ninguno_se_queda_sin_decir():
    from portal import guia
    todos = {p.codigo for r in guia.requisitos() for p in r.puntos}
    for r in guia.requisitos():
        if borradores.con_borrador(r.codigo):
            d = borradores.donde(r.codigo)
            assert set(d.cubre) | set(d.firmado) <= todos
            dichos = set(d.cubre) | set(d.firmado) | {c for c, _ in d.aparte}
            assert {p.codigo for p in r.puntos} <= dichos, r.codigo  # cada punto suyo: dónde, o qué hace falta


# --- Recorridos ---

def test_el_boton_sale_en_los_que_piden_un_documento_y_no_en_los_demas(cliente):
    """También en los que no tienen plantilla propia: con la base genérica."""
    con = cliente.get("/requisitos/5.2").text
    assert 'action="/requisitos/5.2/borrador" data-descargar' in con and "Borrador del documento" in con
    generica = cliente.get("/requisitos/7.2").text
    assert 'action="/requisitos/7.2/borrador"' in generica and "Base para empezar el documento" in generica
    for codigo in ("7.3", "8.1"):  # solo prácticas o registros; puntos que se cumplen con otros
        assert "/borrador" not in cliente.get(f"/requisitos/{codigo}").text
        assert cliente.post(f"/requisitos/{codigo}/borrador").status_code == 404


def test_descarga_el_borrador_con_los_datos_de_la_empresa(cliente):
    cliente.post("/declaracion/cuestionario/nombre", data={"valor": "Ejemplo, S.L."})
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    r = cliente.post("/requisitos/4.3/borrador")
    assert r.status_code == 200
    assert unquote(r.headers["content-disposition"]).endswith("Alcance del sistema de gestion de la IA - borrador 2026-10-07.docx")
    textos = " ".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert "Alcance del sistema de gestión de la IA de Ejemplo, S.L." in textos and "ChatGPT" in textos
    assert "borrador del documento descargado" in cliente.get("/actividad").text


def test_descarga_la_base_generica(cliente):
    r = cliente.post("/requisitos/7.4/borrador")
    assert r.status_code == 200 and unquote(r.headers["content-disposition"]).endswith(" - base 2026-10-07.docx")
    textos = " ".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert "7.4.a" in textos and "Lo que no va en este documento" in textos


def test_la_4_1_y_la_4_2_usan_la_plantilla_de_contexto_con_el_papel_y_los_sistemas(cliente):
    cliente.post("/declaracion/cuestionario/nombre", data={"valor": "Ejemplo, S.L."})
    cliente.post("/declaracion/cuestionario/desarrolla", data={"valor": "no"})
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    for codigo in ("4.1", "4.2"):
        assert "Borrador del documento" in cliente.get(f"/requisitos/{codigo}").text
        r = cliente.post(f"/requisitos/{codigo}/borrador")
        assert unquote(r.headers["content-disposition"]).endswith("Contexto y partes interesadas - borrador 2026-10-07.docx")
    doc = Document(io.BytesIO(r.content))
    textos = " ".join(p.text for p in doc.paragraphs) + " ".join(c.text for t in doc.tables for f in t.rows for c in f.cells)
    assert "Contexto y partes interesadas de Ejemplo, S.L." in textos and "ChatGPT" in textos
    assert "No desarrollamos sistemas de IA" in textos and "Desarrollamos sistemas de IA o los" not in textos
    assert "Partes interesadas" in textos and "Sí: es obligatorio" in textos


def test_la_ficha_dice_donde_subir_el_borrador(cliente):
    ficha = cliente.get("/requisitos/4.1").text
    assert "Cuando esté completo, súbelo a:" in ficha and '<a href="/requisitos/4.2#4.2.a">4.2.a</a>' in ficha
    assert "No cubre:" in ficha and '<a href="/requisitos/4.1#4.1.d">4.1.d</a>' in ficha
    assert "Firmado, súbelo también a:" in cliente.get("/requisitos/5.2").text


# --- Recorrido: el aviso de «Empresa» en la ficha y en Inicio (también con las preguntas abiertas) ---

def test_inicio_y_el_borrador_avisan_de_lo_que_falta_de_la_empresa_hasta_completarlo(tmp_path):
    from portal import guia
    with en_portal(tmp_path / "general" / "portal.db", hoy=lambda: DIA) as c:
        total = len(guia.DATOS_EMPRESA) + len(guia.PREGUNTAS) + len(guia.ABIERTAS)
        ficha, inicio = c.get("/requisitos/4.1").text, c.get("/").text
        assert f"Te quedan {total} preguntas por aclarar" in ficha and f"Te quedan {total} preguntas por aclarar" in inicio
        assert 'href="/empresa">Contestarlas' in ficha

        for clave, _, ejemplo in guia.DATOS_EMPRESA:
            c.post(f"/declaracion/cuestionario/{clave}", data={"valor": ejemplo})
        for q in guia.ABIERTAS:
            c.post(f"/empresa/respuesta/{q.clave}", data={"valor": q.ejemplo})
        for q in guia.PREGUNTAS[:-1]:
            c.post(f"/declaracion/cuestionario/{q.clave}", data={"valor": "no"})
        assert "Te queda 1 pregunta por aclarar" in c.get("/").text
        c.post(f"/declaracion/cuestionario/{guia.PREGUNTAS[-1].clave}", data={"valor": "nose"})
        assert "Te queda 1 pregunta por aclarar" in c.get("/").text  # «No lo sé» sigue pendiente

        c.post(f"/declaracion/cuestionario/{guia.PREGUNTAS[-1].clave}", data={"valor": "si"})
        ficha, inicio = c.get("/requisitos/4.1").text, c.get("/").text
        assert "por aclarar" not in ficha + inicio
        assert 'href="/empresa">«Empresa»' in ficha  # el enlace del texto de ayuda sigue
