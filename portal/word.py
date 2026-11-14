# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Convertir un texto con marcas sencillas en un Word (el acta 9.3 y los borradores de documentos).

Entiende lo justo: «# » título, «## » apartado, «- » lista, «1. » lista numerada, tablas con «|», **negrita** y los
[POR COMPLETAR: …] y [A CONFIRMAR: …] (lo que propone la IA y alguien tiene que revisar), que salen en negrita y
resaltados en amarillo para que no se escape ninguno.
"""
import io
import re
import zipfile
from datetime import datetime

POR_COMPLETAR = re.compile(r"(\[(?:POR COMPLETAR|A CONFIRMAR)[^\]]*\])")
_NEGRITA = re.compile(r"(\*\*[^*]+\*\*)")


def _texto(parrafo, linea: str) -> None:
    """Añade la línea al párrafo, con las negritas y los [POR COMPLETAR] resaltados."""
    from docx.enum.text import WD_COLOR_INDEX
    for trozo in POR_COMPLETAR.split(linea):
        if not trozo:
            continue
        if POR_COMPLETAR.fullmatch(trozo):
            run = parrafo.add_run(trozo)
            run.bold = True
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            continue
        for parte in _NEGRITA.split(trozo):
            if parte:
                negrita = _NEGRITA.fullmatch(parte)
                parrafo.add_run(parte[2:-2] if negrita else parte).bold = bool(negrita)


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


# La marca de todos los Word y PDF que genera el portal: en las propiedades del archivo (clic derecho, «Propiedades»,
# «Detalles»), nunca en el texto que lee el auditor. Dice con qué programa se hizo, no quién es el autor
PROGRAMA = "Portal ISO 42001 · Desarrollado en Movired"
COMENTARIO = "Generado con el Portal ISO 42001. Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0."


def guardar(doc) -> bytes:
    """Guarda un Word de python-docx con la marca en sus propiedades (y sin las de la librería: «python-docx» como
    autor, «Microsoft Macintosh Word» como programa y la fecha de 2013 de su plantilla)."""
    propiedades = doc.core_properties
    propiedades.author = ""
    propiedades.last_modified_by = ""
    propiedades.comments = COMENTARIO
    propiedades.created = propiedades.modified = datetime.now()
    salida = io.BytesIO()
    doc.save(salida)
    entrada, salida = zipfile.ZipFile(io.BytesIO(salida.getvalue())), io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as nuevo:
        for parte in entrada.infolist():
            datos = entrada.read(parte)
            if parte.filename == "docProps/app.xml":
                datos = re.sub(rb"<Application>[^<]*</Application>",
                               f"<Application>{PROGRAMA}</Application>".encode("utf-8"), datos)
            nuevo.writestr(parte, datos)
    return salida.getvalue()


def documento(texto: str, aviso: str = "", unir_lineas: bool = False) -> bytes:
    """`unir_lineas`: el texto viene cortado a mano (las plantillas) y las líneas seguidas son un mismo párrafo; si no
    (lo que escribe Claude), cada línea es un párrafo."""
    from docx import Document
    doc = Document()
    if aviso:
        doc.add_paragraph().add_run(aviso).italic = True
    lineas = texto.strip().splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        if linea.lstrip().startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].lstrip().startswith("|"):
                if not re.fullmatch(r"\s*\|[\s|:-]+\|?\s*", lineas[i]):  # la fila «|---|---|» no es una fila
                    filas.append(_celdas(lineas[i]))
                i += 1
            columnas = max(len(f) for f in filas)
            tabla = doc.add_table(rows=len(filas), cols=columnas)
            tabla.style = "Table Grid"
            for n, fila in enumerate(filas):
                for m, celda in enumerate(fila):
                    p = tabla.cell(n, m).paragraphs[0]
                    _texto(p, celda)
                    if n == 0:
                        for run in p.runs:
                            run.bold = True
            continue
        if linea.startswith("# "):
            doc.add_heading(linea[2:].strip(), level=0)
        elif linea.startswith("## "):
            doc.add_heading(linea[3:].strip(), level=1)
        elif re.match(r"^\s*[-*]\s+", linea) or re.match(r"^\s*\d+\.\s+", linea):
            estilo = "List Bullet" if re.match(r"^\s*[-*]\s+", linea) else "List Number"
            partes = [re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", linea)]
            # Un elemento puede seguir en las líneas de abajo, con sangría
            while unir_lineas and i + 1 < len(lineas) and re.match(r"^\s+\S", lineas[i + 1]) and not re.match(r"^\s*(?:[-*]|\d+\.)\s", lineas[i + 1]):
                i += 1
                partes.append(lineas[i].strip())
            _texto(doc.add_paragraph(style=estilo), " ".join(partes))
        elif linea.strip():
            # Un párrafo puede seguir en las líneas siguientes (el texto de las plantillas va cortado a mano)
            partes = [linea.strip()]
            while (unir_lineas and i + 1 < len(lineas) and lineas[i + 1].strip() and not re.match(r"^(#|\s*[-*]\s|\s*\d+\.\s|\s*\|)", lineas[i + 1])):
                i += 1
                partes.append(lineas[i].strip())
            _texto(doc.add_paragraph(), " ".join(partes))
        i += 1
    return guardar(doc)
