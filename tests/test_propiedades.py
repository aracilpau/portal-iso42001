# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La marca de los Word y PDF que genera el portal: va en las propiedades del archivo (con qué programa se hizo) y
nunca en el texto que lee el auditor."""
import io
import zipfile
from datetime import date

from docx import Document

from portal import documento, word
from portal.db import Decision

MARCA = "Desarrollado en Movired"


def _texto_word(datos: bytes) -> str:
    doc = Document(io.BytesIO(datos))
    celdas = [c.text for t in doc.tables for f in t.rows for c in f.cells]
    return "\n".join([p.text for p in doc.paragraphs] + celdas)


def _filas():
    return documento.filas({"A.2.2": Decision(aplica=True, porque="Tenemos una política de IA.", fecha=date(2026, 11, 14))})


def _comprobar_word(datos: bytes):
    propiedades = Document(io.BytesIO(datos)).core_properties
    assert propiedades.comments == word.COMENTARIO
    assert propiedades.author == "" and propiedades.last_modified_by == ""
    assert propiedades.created.year >= 2026
    app = zipfile.ZipFile(io.BytesIO(datos)).read("docProps/app.xml").decode("utf-8")
    assert f"<Application>{word.PROGRAMA}</Application>" in app
    assert MARCA not in _texto_word(datos)


# --- Piezas ---

def test_los_borradores_y_el_acta_llevan_la_marca_en_las_propiedades_y_no_en_el_texto():
    _comprobar_word(word.documento("# Política de IA\n\nTexto del borrador.\n\n- [POR COMPLETAR: fecha]",
                                   aviso="Borrador: revísalo."))


def test_la_declaracion_en_word_lleva_la_marca_en_las_propiedades_y_no_en_el_texto():
    _comprobar_word(documento.word(_filas(), "Ejemplo, S.L.", date(2026, 11, 14)))


def test_la_declaracion_en_pdf_lleva_la_marca_en_las_propiedades_y_no_en_el_texto():
    from pypdf import PdfReader
    lector = PdfReader(io.BytesIO(documento.pdf(_filas(), "Ejemplo, S.L.", date(2026, 11, 14))))
    assert lector.metadata.creator == word.PROGRAMA
    assert lector.metadata.subject == word.COMENTARIO
    assert not lector.metadata.author
    assert MARCA not in "".join(p.extract_text() for p in lector.pages)
