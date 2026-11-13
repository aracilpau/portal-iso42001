# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El revisor de archivos («Revisar con IA», antes «¿Me vale?»). Ninguna prueba llama a Claude."""
import io
import json
import os
from datetime import date, datetime
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from openpyxl import Workbook

from portal import db, ia, lectura, revisor
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 3, 15)
HX = {"HX-Request": "true"}
EJEMPLOS = Path(__file__).resolve().parent / "archivos"


class ClaudeDeMentira:
    def __init__(self, respuesta="", falla=None):
        self.respuesta, self.falla, self.llamadas = respuesta, falla, []

    async def __call__(self, nombre, instrucciones, mensaje, esfuerzo="medium", imagenes=None):
        self.llamadas.append({"nombre": nombre, "mensaje": mensaje, "esfuerzo": esfuerzo, "imagenes": imagenes or []})
        if self.falla:
            raise ia.ClaudeNoDisponible(self.falla)
        return self.respuesta


SI = """VEREDICTO: SÍ
POR QUÉ: La política habla del Asistente de reservas y de ChatGPT, que es lo que usa la empresa.
SE APOYA EN: politica-ia-ejemplo.docx, apartado 1
LE FALTA: nada"""
NO = """VEREDICTO: NO
POR QUÉ: Es una política de manual: valdría igual para cualquier empresa.
SE APOYA EN: politica-ia-generica.pdf, página 1
LE FALTA: Nombrar los sistemas de IA de la empresa y para qué los usa."""


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def claude(monkeypatch):
    falso = ClaudeDeMentira(SI)
    monkeypatch.setattr(ia, "tarea", falso)
    monkeypatch.setattr(ia, "disponible", lambda: True)
    return falso


@pytest.fixture
def cliente(bd, claude):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


def subir(cliente, url, nombre, contenido):
    return cliente.post(f"{url}/archivos", files=[("archivos", (nombre, contenido, "application/octet-stream"))])


def revision(html, ancla):
    i = html.index(f'id="revision-{ancla}"')
    return html[i:html.index('<div class="revision"', i + 10) if html.find('<div class="revision"', i + 10) > 0 else len(html)]


# --- Piezas: leer los archivos ---

def test_lee_los_dos_ejemplos():
    buena = lectura.leer(EJEMPLOS / "politica-ia-ejemplo.docx")
    assert not buena.aviso and "Asistente de reservas" in buena.texto and "director general" in buena.texto
    generica = lectura.leer(EJEMPLOS / "politica-ia-generica.pdf")
    assert not generica.aviso and generica.texto.startswith("[Página 1]") and "La organización reconoce" in generica.texto


def test_lee_word_con_tablas_excel_texto_e_imagenes(tmp_path):
    doc = Document()
    doc.add_paragraph("Matriz de competencias")
    t = doc.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text, t.cell(1, 0).text, t.cell(1, 1).text = "Rol", "Formación", "Responsable", "Curso 42001"
    doc.save(tmp_path / "matriz.docx")
    assert "[Tabla 1]\nRol | Formación\nResponsable | Curso 42001" in lectura.leer(tmp_path / "matriz.docx").texto
    libro = Workbook()
    libro.active.title = "Riesgos"
    libro.active.append(["Riesgo", "Nivel"])
    libro.active.append(["Sesgo", "Alto"])
    libro.save(tmp_path / "riesgos.xlsx")
    assert lectura.leer(tmp_path / "riesgos.xlsx").texto == "[Hoja «Riesgos»]\nRiesgo | Nivel\nSesgo | Alto"
    (tmp_path / "acta.txt").write_text("Acta de aprobación", encoding="utf-8")
    assert lectura.leer(tmp_path / "acta.txt").texto == "Acta de aprobación"
    (tmp_path / "foto.png").write_bytes(b"\x89PNG falso")
    foto = lectura.leer(tmp_path / "foto.png")
    assert foto.imagen[0] == "image/png" and not foto.texto


def test_lo_que_no_se_puede_leer_lo_dice(tmp_path):
    (tmp_path / "presentacion.pptx").write_bytes(b"x")
    assert "solo Word, Excel, PDF" in lectura.leer(tmp_path / "presentacion.pptx").aviso
    (tmp_path / "roto.docx").write_bytes(b"no es un word")
    assert "no se ha podido abrir" in lectura.leer(tmp_path / "roto.docx").aviso


def test_un_pdf_escaneado_sin_texto_lo_dice(tmp_path):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.output(str(tmp_path / "escaneado.pdf"))
    assert "sin texto" in lectura.leer(tmp_path / "escaneado.pdf").aviso


def pdf_con_firmas(ruta, firmas):
    """Un PDF con texto y estos campos de firma, inventados: (nombre, fecha) o None si el campo está sin firmar."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
    escritor = PdfWriter(clone_from=PdfReader(EJEMPLOS / "politica-ia-generica.pdf"))
    campos = ArrayObject()
    for n, firma in enumerate(firmas):
        campo = DictionaryObject({NameObject("/FT"): NameObject("/Sig"), NameObject("/T"): TextStringObject(f"Firma{n}")})
        if firma:
            campo[NameObject("/V")] = DictionaryObject({NameObject("/Name"): TextStringObject(firma[0]),
                                                        NameObject("/M"): TextStringObject(firma[1])})
        campos.append(escritor._add_object(campo))
    escritor._root_object[NameObject("/AcroForm")] = DictionaryObject({NameObject("/Fields"): campos})
    escritor.write(ruta)


def test_un_pdf_firmado_dice_quien_y_cuando_sin_el_dni(tmp_path):
    ruta = tmp_path / "firmado.pdf"
    pdf_con_firmas(ruta, [("00000000T ANA GARCIA-LOPEZ (R: B00000000)", "D:20261008152534+02'00'"),
                          ("Luis Pérez", "D:20261009")])
    texto = lectura.leer(ruta).texto
    assert texto.startswith(f"[{lectura.AVISO_FIRMAS} Ana Garcia-Lopez, 08/10/2026 15:25 · Luis Pérez, 09/10/2026]")
    assert "00000000T" not in texto and "B00000000" not in texto
    assert "[Página 1]" in texto  # el documento se sigue leyendo


def test_un_campo_de_firma_vacio_no_cuenta_como_firma(tmp_path):
    ruta = tmp_path / "sin_firmar.pdf"
    pdf_con_firmas(ruta, [None])
    assert lectura.AVISO_FIRMAS not in lectura.leer(ruta).texto
    assert lectura.AVISO_FIRMAS not in lectura.leer(EJEMPLOS / "politica-ia-generica.pdf").texto


def test_si_no_se_pueden_mirar_las_firmas_el_pdf_se_lee_igual(tmp_path, monkeypatch):
    ruta = tmp_path / "firmado.pdf"
    pdf_con_firmas(ruta, [("Ana", "D:20261008")])
    monkeypatch.setattr(lectura, "_nombre_firmante", lambda n: 1 / 0)
    leido = lectura.leer(ruta)
    assert not leido.aviso and "[Página 1]" in leido.texto and lectura.AVISO_FIRMAS not in leido.texto


def test_la_ia_sabe_que_las_firmas_son_solo_un_indicio():
    # Las instrucciones citan el comienzo del aviso: si uno cambia sin el otro, la IA no sabría a qué línea se refieren
    comienzo = "Firmas digitales guardadas en el PDF"
    assert lectura.AVISO_FIRMAS.startswith(comienzo) and f"«{comienzo}»" in " ".join(revisor.INSTRUCCIONES.split())
    assert "cuéntalo como indicio" in " ".join(revisor.INSTRUCCIONES.split())


def test_demasiado_largo_no_se_manda_a_medias(tmp_path, monkeypatch):
    monkeypatch.setattr(lectura, "TOPE", 10)
    (tmp_path / "largo.txt").write_text("x" * 50, encoding="utf-8")
    _, aviso = lectura.leer_todos([tmp_path / "largo.txt"])
    assert "demasiado largos" in aviso


# --- Piezas: la respuesta de Claude y la huella ---

def test_lee_la_respuesta_con_la_forma_pedida():
    r = revisor.leer(NO)
    assert r.veredicto == revisor.NO and r.falta.startswith("Nombrar") and "página 1" in r.apoyo
    assert revisor.leer(SI).veredicto == revisor.SI and revisor.leer(SI).falta == ""
    nose = revisor.leer("**VEREDICTO:** NO SE PUEDE SABER\n**POR QUE:** No se puede leer el archivo.\nLE FALTA: nada")
    assert nose.veredicto == revisor.NO_SE
    # Lo que el borrador deja por completar sale al revisarlo
    assert "Un [POR COMPLETAR] en lo que pide el punto es algo que falta: el veredicto es NO" in revisor.INSTRUCCIONES
    # Un archivo que no tiene que ver con el punto es un NO, y lo dice
    assert "no tienen nada que ver con el punto, el veredicto es NO" in revisor.INSTRUCCIONES
    assert "NO SE PUEDE SABER solo si los archivos no se pueden leer" in revisor.INSTRUCCIONES


def test_sin_la_forma_pedida_no_vale():
    assert revisor.leer("Creo que sí cumple.") is None
    assert revisor.leer("VEREDICTO: SÍ\nVEREDICTO: NO\nPOR QUÉ: dudo") is None   # dos veredictos
    assert revisor.leer("VEREDICTO: SÍ") is None                                  # sin porqué


def test_la_huella_cambia_si_cambian_los_archivos(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("uno", encoding="utf-8")
    h1 = revisor.huella([a])
    assert revisor.huella([a]) == h1
    a.write_text("uno y dos", encoding="utf-8")
    assert revisor.huella([a]) != h1



def test_la_huella_no_cambia_si_solo_cambia_la_fecha(tmp_path):
    # OneDrive y Teams pueden cambiar la fecha sin tocar el archivo; no es motivo para volver a revisar
    a = tmp_path / "a.txt"
    a.write_text("uno", encoding="utf-8")
    h1 = revisor.huella([a])
    os.utime(a, ns=(a.stat().st_atime_ns, a.stat().st_mtime_ns + 1_500_000_000))
    assert revisor.huella([a]) == h1


def test_la_huella_cambia_si_se_anade_o_se_quita_un_archivo(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("uno", encoding="utf-8")
    h1 = revisor.huella([a])
    b.write_text("dos", encoding="utf-8")
    assert revisor.huella([a, b]) != h1
    b.unlink()
    assert revisor.huella([a, b]) == h1


def test_las_revisiones_de_antes_de_la_v5_siguen_valiendo(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("uno", encoding="utf-8")
    antigua = revisor.huella_antigua([a])
    assert antigua != revisor.huella([a])
    assert revisor.vigente([a], antigua) and revisor.vigente([a], revisor.huella([a]))
    a.write_text("uno y dos", encoding="utf-8")
    assert not revisor.vigente([a], antigua)


def test_el_mensaje_lleva_el_punto_la_empresa_y_los_archivos():
    perfil = {"datos": {"nombre": "Ejemplo, S.L."}, "respuestas": {"desarrolla": "si"}}
    leidos = [lectura.leer(EJEMPLOS / "politica-ia-ejemplo.docx"), lectura.Leido("foto.png", imagen=("image/png", "x")),
              lectura.Leido("raro.pptx", aviso="no se puede")]
    m = revisor.mensaje("5.2.a", perfil, leidos)
    assert "Punto 5.2.a (Documento): Que la política sea apropiada" in m and "Te pedirán:" in m
    assert "- Nombre de la empresa: Ejemplo, S.L." in m and "→ Sí" in m
    assert "## politica-ia-ejemplo.docx\n<<<\n" in m and "(Es una imagen: va adjunta.)" in m and "No se ha podido leer" in m


# --- Recorridos ---

def test_me_vale_sale_solo_con_archivos_y_guarda_la_respuesta(cliente, claude, bd):
    url = "/requisitos/5.2/puntos/5.2.a"
    assert 'hx-post="/requisitos/5.2/puntos/5.2.a/revisar"' not in cliente.get("/requisitos/5.2").text
    subir(cliente, url, "politica-ia-ejemplo.docx", (EJEMPLOS / "politica-ia-ejemplo.docx").read_bytes())
    ficha = cliente.get("/requisitos/5.2").text
    assert 'hx-post="/requisitos/5.2/puntos/5.2.a/revisar"' in ficha and "Revisar con IA" in ficha and "¿Me vale?" not in ficha
    r = cliente.post(f"{url}/revisar", headers=HX)
    llamada = claude.llamadas[-1]
    assert llamada["nombre"] == "revisor" and llamada["esfuerzo"] == "high" and "Asistente de reservas" in llamada["mensaje"]
    caja = revision(r.text, "5.2.a")
    assert "SÍ, parece que cubre 5.2.a" in caja and "Volver a revisar" in caja and "apartado 1" in caja
    assert "Antigua" not in caja
    assert not db.marcas(bd, 1)                                    # no marca nada
    assert "revisado por la IA" in cliente.get("/actividad").text


def test_si_cambian_los_archivos_la_revision_pasa_a_antigua(cliente, claude):
    url = "/requisitos/5.2/puntos/5.2.a"
    subir(cliente, url, "politica.pdf", (EJEMPLOS / "politica-ia-generica.pdf").read_bytes())
    claude.respuesta = NO
    caja = revision(cliente.post(f"{url}/revisar", headers=HX).text, "5.2.a")
    assert "NO, le falta algo" in caja and "Le falta:</strong> Nombrar los sistemas" in caja
    subir(cliente, url, "acta.txt", b"Acta de aprobacion")
    caja = revision(cliente.get("/requisitos/5.2").text, "5.2.a")
    # Queda claro que lo que dijo es de la versión anterior, no de lo que hay ahora
    assert "Esta revisión es de una versión anterior de los archivos" in caja and "Volver a revisar" in caja
    assert "NO en la versión anterior" in caja and "NO, le falta algo" not in caja
    assert caja.index("versión anterior de los archivos") < caja.index("NO en la versión anterior")  # el aviso, lo primero



def test_una_revision_guardada_antes_de_la_v5_no_sale_como_antigua(cliente, bd):
    # Las de vuestro portal se guardaron con la huella con fecha: siguen valiendo mientras no cambien los archivos
    url = "/requisitos/5.2/puntos/5.2.a"
    subir(cliente, url, "politica.pdf", (EJEMPLOS / "politica-ia-generica.pdf").read_bytes())
    archivo = bd.parent / "pruebas" / "5.2" / "5.2.a" / "politica.pdf"
    db.guardar_revision(bd, 1, "5.2.a", 0, "si", "Vale.", "", "", revisor.huella_antigua([archivo]),
                        datetime(2026, 10, 7, 10))
    caja = revision(cliente.get("/requisitos/5.2").text, "5.2.a")
    assert "Vale." in caja and "versión anterior" not in caja
    # Si después cambian los archivos, sí avisa
    subir(cliente, url, "acta.txt", b"Acta de aprobacion")
    assert "versión anterior de los archivos" in revision(cliente.get("/requisitos/5.2").text, "5.2.a")


def test_si_el_pdf_tiene_firmas_avisa_de_que_estan_sin_comprobar(cliente, claude, tmp_path):
    url, aviso = "/requisitos/5.2/puntos/5.2.e", "Firma sin comprobar"
    firmado = tmp_path / "firmado.pdf"
    pdf_con_firmas(firmado, [("00000000T ANA GARCIA (R: B00000000)", "D:20261008152534+02'00'")])
    subir(cliente, url, "firmado.pdf", firmado.read_bytes())
    cliente.post(f"{url}/revisar", headers=HX)
    caja = revision(cliente.get("/requisitos/5.2").text, "5.2.e")  # sigue al volver a la ficha
    assert aviso in caja and "Ana Garcia, 08/10/2026 15:25" in caja and "Ábrelo en Adobe" in caja
    assert "00000000T" not in caja
    assert "SÍ, parece que cubre" in caja                          # el SÍ sigue, con el aviso delante
    assert caja.index(aviso) < caja.index("SÍ, parece que cubre")
    # Si los archivos cambian, manda el aviso de la versión anterior
    subir(cliente, url, "acta.txt", b"Acta")
    caja = revision(cliente.get("/requisitos/5.2").text, "5.2.e")
    assert aviso not in caja and "versión anterior" in caja
    # Sin el PDF firmado, al volver a revisar el aviso desaparece
    cliente.post(f"{url}/archivos/firmado.pdf/quitar")
    assert aviso not in revision(cliente.post(f"{url}/revisar", headers=HX).text, "5.2.e")


def test_sin_firmas_no_avisa(cliente, claude):
    url = "/requisitos/5.2/puntos/5.2.a"
    subir(cliente, url, "politica.pdf", (EJEMPLOS / "politica-ia-generica.pdf").read_bytes())
    assert "Firma sin comprobar" not in revision(cliente.post(f"{url}/revisar", headers=HX).text, "5.2.a")


def test_las_imagenes_van_como_imagen(cliente, claude):
    url = "/requisitos/5.2/puntos/5.2.f"
    subir(cliente, url, "intranet.png", b"\x89PNG captura")
    cliente.post(f"{url}/revisar", headers=HX)
    assert claude.llamadas[-1]["imagenes"][0][0] == "image/png"


def test_una_linea_de_sistema_se_revisa_aparte(cliente, claude, bd):
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    url = "/requisitos/8.4/puntos/8.4.a/sistemas/1"
    subir(cliente, url, "evaluacion.txt", b"Evaluacion de impacto de ChatGPT")
    r = cliente.post(f"{url}/revisar", headers=HX)
    assert "# El punto 8.4.a · en el sistema «ChatGPT»" in claude.llamadas[-1]["mensaje"]
    assert "SÍ, parece que cubre 8.4.a" in revision(r.text, "8.4.a-1")
    assert set(db.revisiones(bd, 1, ["8.4.a"])) == {("8.4.a", 1)}


def test_sin_archivos_sin_claude_o_respuesta_rara_lo_dice(cliente, claude, bd):
    url = "/requisitos/5.2/puntos/5.2.a"
    assert "Sube antes algún archivo" in cliente.post(f"{url}/revisar", headers=HX).text
    subir(cliente, url, "politica.docx", (EJEMPLOS / "politica-ia-ejemplo.docx").read_bytes())
    claude.respuesta = "Me parece que está bien."
    assert "No se pudo comprobar" in cliente.post(f"{url}/revisar", headers=HX).text
    claude.falla = "Claude no está disponible: no se encuentra Claude Code en este ordenador."
    assert "no se encuentra Claude Code" in cliente.post(f"{url}/revisar", headers=HX).text
    assert not db.revisiones(bd, 1, ["5.2.a"])


def test_no_se_revisa_lo_que_no_se_marca_a_mano(cliente):
    assert cliente.post("/requisitos/7.3/puntos/7.3.a/revisar").status_code == 400   # apoyado
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    assert cliente.post("/requisitos/A.10.4/puntos/A.10.4.a/revisar").status_code == 400  # no aplica
