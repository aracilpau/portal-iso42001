# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El documento de la Declaración de Aplicabilidad para el auditor, en Word o PDF.

Se genera solo al pedirlo, con lo que haya decidido en ese momento.
"""
import io
from dataclasses import dataclass
from datetime import date

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Cm, Pt
from fpdf import FPDF
from fpdf.fonts import FontFace

from portal import guia
from portal.db import Decision

TITULO = "Declaración de Aplicabilidad"
NOMBRE = "Declaracion de Aplicabilidad"   # los archivos se llaman así, sin tilde, para que nada falle al abrirlos
FORMATOS = {"word": ".docx", "pdf": ".pdf"}


@dataclass
class Fila:
    codigo: str
    titulo: str
    aplica: str   # «Aplica», «No aplica» o «Sin decidir»
    porque: str
    fecha: str


def filas(decisiones: dict[str, Decision]) -> list[Fila]:
    """Los 38 controles del Anexo A, en el orden de la norma."""
    res = []
    for r in guia.requisitos():
        if r.obligatorio:
            continue
        d = decisiones.get(r.codigo)
        res.append(Fila(r.codigo, r.titulo,
                        "Sin decidir" if d is None else "Aplica" if d.aplica else "No aplica",
                        d.porque if d else "", d.fecha.strftime("%d/%m/%Y") if d else ""))
    return res


def nombre_archivo(formato: str, hoy: date) -> str:
    return f"{NOMBRE} {hoy.isoformat()}{FORMATOS[formato]}"


def _resumen(fs: list[Fila]) -> str:
    aplican = sum(f.aplica == "Aplica" for f in fs)
    no = sum(f.aplica == "No aplica" for f in fs)
    sin = len(fs) - aplican - no
    texto = (f"{len(fs)} controles del Anexo A de la ISO/IEC 42001: {aplican} aplica{'n' if aplican != 1 else ''}"
             f" y {no} no aplica{'n' if no != 1 else ''}.")
    if sin:
        texto += f" Quedan {sin} sin decidir: este documento no está completo."
    return texto


def word(fs: list[Fila], espacio: str, hoy: date) -> bytes:
    doc = Document()
    seccion = doc.sections[0]
    seccion.orientation = WD_ORIENT.LANDSCAPE
    seccion.page_width, seccion.page_height = seccion.page_height, seccion.page_width
    for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(seccion, lado, Cm(1.8))
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    doc.add_heading(TITULO, level=1)
    doc.add_paragraph(f"{espacio} · ISO/IEC 42001, punto 6.1.3 · Generada el {hoy.strftime('%d/%m/%Y')}")
    doc.add_paragraph(_resumen(fs))

    tabla = doc.add_table(rows=1, cols=5)
    tabla.style = "Light Grid Accent 1"
    for celda, texto in zip(tabla.rows[0].cells, ("Control", "Título", "¿Aplica?", "Por qué", "Decidido el")):
        celda.text = texto
    for f in fs:
        for celda, texto in zip(tabla.add_row().cells, (f.codigo, f.titulo, f.aplica, f.porque, f.fecha)):
            celda.text = texto
    for fila in tabla.rows:
        for celda, ancho in zip(fila.cells, (2.2, 6, 2.4, 11.5, 2.6)):
            celda.width = Cm(ancho)

    salida = io.BytesIO()
    doc.save(salida)
    return salida.getvalue()


def _latin(texto: str) -> str:
    # Las fuentes de serie del PDF solo tienen los caracteres de Europa occidental
    cambios = {"→": "->", "≥": ">=", "≤": "<=", "…": "...", "‑": "-", "−": "-"}
    texto = "".join(cambios.get(c, c) for c in texto)
    return texto.encode("cp1252", "replace").decode("cp1252")


def pdf(fs: list[Fila], espacio: str, hoy: date) -> bytes:
    doc = FPDF(orientation="L", format="A4")
    doc.set_auto_page_break(True, margin=15)
    doc.set_margins(15, 15, 15)
    doc.add_page()
    doc.set_font("Helvetica", "B", 16)
    doc.cell(0, 10, _latin(TITULO), new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", "", 10)
    doc.cell(0, 6, _latin(f"{espacio} · ISO/IEC 42001, punto 6.1.3 · Generada el {hoy.strftime('%d/%m/%Y')}"),
             new_x="LMARGIN", new_y="NEXT")
    doc.multi_cell(0, 6, _latin(_resumen(fs)), new_x="LMARGIN", new_y="NEXT")
    doc.ln(3)

    anchos = (20, 62, 22, 135, 28)
    doc.set_font("Helvetica", "", 9)
    with doc.table(col_widths=anchos, text_align="LEFT", line_height=5,
                   headings_style=FontFace(emphasis="BOLD", fill_color=(235, 235, 225))) as tabla:
        fila = tabla.row()
        for texto in ("Control", "Título", "¿Aplica?", "Por qué", "Decidido el"):
            fila.cell(_latin(texto))
        for f in fs:
            fila = tabla.row()
            for texto in (f.codigo, f.titulo, f.aplica, f.porque, f.fecha):
                fila.cell(_latin(texto))
    return bytes(doc.output())


def generar(formato: str, fs: list[Fila], espacio: str, hoy: date) -> bytes:
    return word(fs, espacio, hoy) if formato == "word" else pdf(fs, espacio, hoy)
