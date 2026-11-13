# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Pasar los archivos de un punto a algo que Claude pueda leer.

Word, Excel, PDF y texto se convierten en texto; las imágenes van como imagen. Lo que no se puede leer lo dice, y lo
que es demasiado largo también: nunca se corta sin avisar.
"""
import base64
import re
from dataclasses import dataclass, field
from pathlib import Path

TOPE = 300_000  # caracteres de texto entre todos los archivos de un punto (unos 80.000 tokens)
IMAGENES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
TEXTO = {".txt", ".md", ".csv"}
AVISO_FIRMAS = "Firmas digitales guardadas en el PDF, sin comprobar su validez:"


@dataclass
class Leido:
    nombre: str
    texto: str = ""          # el contenido en texto, con marcas de página u hoja
    imagen: tuple[str, str] | None = None  # (tipo, base64) si es una imagen
    aviso: str = ""          # si no se ha podido leer, por qué
    firmas: list[str] = field(default_factory=list)  # de un PDF: quién lo firmó digitalmente y cuándo


def _docx(ruta: Path) -> str:
    from docx import Document
    doc = Document(ruta)
    partes = [p.text for p in doc.paragraphs if p.text.strip()]
    for n, tabla in enumerate(doc.tables, 1):
        partes.append(f"[Tabla {n}]")
        for fila in tabla.rows:
            partes.append(" | ".join(c.text.strip() for c in fila.cells))
    return "\n".join(partes)


def _xlsx(ruta: Path) -> str:
    from openpyxl import load_workbook
    libro = load_workbook(ruta, read_only=True, data_only=True)
    partes = []
    for hoja in libro.worksheets:
        partes.append(f"[Hoja «{hoja.title}»]")
        for fila in hoja.iter_rows(values_only=True):
            if any(v is not None and str(v).strip() for v in fila):
                partes.append(" | ".join("" if v is None else str(v) for v in fila))
    libro.close()
    return "\n".join(partes)


def _nombre_firmante(nombre) -> str:
    """Solo el nombre: sin el DNI ni el CIF que suelen llevar los certificados, que no hacen falta para revisar."""
    limpio = re.sub(r"\([^)]*\)|\b(?:NIF|DNI|NIE|CIF|CN)\b[:=]?|\S*\d\S*", " ", str(nombre or ""), flags=re.I)
    limpio = " ".join(limpio.split()).strip(" -–,;:")
    return (limpio.title() if limpio.isupper() else limpio) or "nombre no indicado"


def _fecha_firma(fecha) -> str:
    m = re.match(r"D:(\d{4})(\d\d)(\d\d)(?:(\d\d)(\d\d))?", str(fecha or ""))
    if not m:
        return "fecha no indicada"
    a, mes, d, h, mi = m.groups()
    return f"{d}/{mes}/{a}" + (f" {h}:{mi}" if h else "")


def _firmas(lector) -> list[str]:
    """Quién ha firmado digitalmente el PDF y cuándo. Son datos aparte del texto de las páginas. No comprueba que la
    firma sea válida. Si algo falla al mirarlas, no impide leer el PDF."""
    encontradas = []

    def recorrer(campos, tipo=None):
        for campo in campos or []:
            c = campo.get_object()
            este = c.get("/FT", tipo)
            valor = c.get("/V")
            if este == "/Sig" and valor is not None:
                firma = valor.get_object()
                encontradas.append(f"{_nombre_firmante(firma.get('/Name'))}, {_fecha_firma(firma.get('/M'))}")
            recorrer(c.get("/Kids"), este)

    try:
        formulario = lector.trailer["/Root"].get("/AcroForm")
        if formulario is not None:
            recorrer(formulario.get_object().get("/Fields"))
    except Exception:
        return []
    return encontradas


def _pdf(ruta: Path) -> tuple[str, str, list[str]]:
    from pypdf import PdfReader
    lector = PdfReader(ruta)
    paginas = lector.pages
    partes = [f"[Página {n}]\n{(p.extract_text() or '').strip()}" for n, p in enumerate(paginas, 1)]
    con_texto = sum(bool((p.extract_text() or "").strip()) for p in paginas)
    if paginas and not con_texto:
        return "", "es un PDF sin texto (seguramente escaneado): no se puede leer su contenido", []
    firmas = _firmas(lector)
    if firmas:
        partes.insert(0, f"[{AVISO_FIRMAS} {' · '.join(firmas)}]")
    return "\n\n".join(partes), "", firmas


def leer(ruta: Path) -> Leido:
    """Un archivo, leído. Si no se puede, `aviso` dice por qué."""
    tipo = ruta.suffix.lower()
    try:
        if tipo in IMAGENES:
            return Leido(ruta.name, imagen=(IMAGENES[tipo], base64.b64encode(ruta.read_bytes()).decode("ascii")))
        if tipo == ".docx":
            return Leido(ruta.name, texto=_docx(ruta))
        if tipo == ".xlsx":
            return Leido(ruta.name, texto=_xlsx(ruta))
        if tipo == ".pdf":
            texto, aviso, firmas = _pdf(ruta)
            return Leido(ruta.name, texto=texto, aviso=aviso, firmas=firmas)
        if tipo in TEXTO:
            return Leido(ruta.name, texto=ruta.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:  # un archivo dañado no debe tumbar la revisión de los demás
        return Leido(ruta.name, aviso=f"no se ha podido abrir ({type(e).__name__})")
    return Leido(ruta.name, aviso=f"los archivos {tipo or 'sin extensión'} no se pueden revisar (solo Word, Excel, PDF, "
                                  "imágenes y texto)")


def leer_todos(rutas: list[Path]) -> tuple[list[Leido], str]:
    """Los archivos de un punto. Si entre todos pasan del tope, se devuelve el aviso y no se manda nada a medias."""
    leidos = [leer(r) for r in rutas]
    total = sum(len(l.texto) for l in leidos)
    if total > TOPE:
        return leidos, (f"Los archivos son demasiado largos para revisarlos de una vez ({total // 1000} mil caracteres; "
                        f"el máximo es {TOPE // 1000} mil). Revisa por separado o sube solo lo necesario.")
    return leidos, ""
