# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los borradores de documentos, que redacta la IA.

Cada plantilla de `guia/plantillas/` (igual para cualquier empresa) se rellena con el cuestionario y el inventario:
- huecos: {nombre}, {actividad}, {tamaño}, {direccion}, {fecha} y {sistemas}; si falta el dato, [POR COMPLETAR: …];
- apartados: «[si clave] … [/si]» sale si la respuesta es Sí; «[si no clave] … [/si]», si es No. Con «No lo sé» o sin
  contestar, el de «si» sale con un aviso para confirmarlo, y el de «si no», no.
El resultado es un Word para descargar; no es una prueba hasta que se aprueba y se sube.

Los requisitos sin plantilla propia que piden algún documento tienen una **genérica**: una base para
empezar a escribir, montada con la guía: un apartado por cada punto que se demuestra con un documento, con lo que tiene
que decir y lo que pedirá el auditor, y al final lo que no va en el documento. No inventa nada de la empresa.

**Con IA:** ese borrador sin IA es la estructura fija. Claude lo redacta en formal con lo
que se sabe de la empresa (el cuestionario, también las abiertas y las preguntas de la IA contestadas, el inventario y
las notas «Cómo lo hacemos aquí»), sin tocar los títulos, y añade al final «Lo que falta saber». El portal comprueba que
los títulos son los mismos; si no, o sin Claude, sale el borrador sin IA con un aviso. Nunca lee los archivos
subidos.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from portal import guia

CARPETA = Path(__file__).resolve().parent.parent / "guia" / "plantillas"

# Qué plantilla corresponde a cada requisito, y su nombre (para el archivo)
PLANTILLAS = {"5.2": "politica-ia", "A.2.2": "politica-ia", "4.3": "alcance", "5.3": "roles", "A.3.2": "roles",
              "6.1.2": "riesgos-impacto", "6.1.4": "riesgos-impacto", "6.2": "objetivos", "7.5": "documentacion",
              "9.2": "auditoria-interna", "10.2": "no-conformidades", "4.1": "contexto", "4.2": "contexto"}
NOMBRES = {"politica-ia": "Politica de IA", "alcance": "Alcance del sistema de gestion de la IA",
           "roles": "Roles y responsabilidades", "riesgos-impacto": "Procedimiento de riesgos y de impacto",
           "objetivos": "Objetivos de IA", "documentacion": "Control de la documentacion",
           "auditoria-interna": "Programa de auditoria interna", "no-conformidades": "No conformidades y acciones correctivas",
           "contexto": "Contexto y partes interesadas"}
HUECOS = ("nombre", "actividad", "tamaño", "direccion", "fecha", "sistemas")
AVISO = "Borrador hecho con la plantilla del portal. Complétalo, revísalo y apruébalo antes de usarlo."
AVISO_IA = "Borrador hecho con IA. Revísalo y apruébalo antes de usarlo."
AVISO_SIN_IA = "Hecho sin IA: {motivo} " + AVISO
AVISO_GENERICA = ("Base para empezar a escribir, hecha con la guía del portal: no lleva nada de la empresa salvo el "
                  "nombre. Sustituye cada [POR COMPLETAR] por lo vuestro, revísalo y apruébalo antes de usarlo.")

_BLOQUE = re.compile(r"^\[si (no )?([\w]+)\][ \t]*\n(.*?)^\[/si\][ \t]*\n?", re.M | re.S)
_HUECO = re.compile(r"\{([\wñ]+)\}")


def plantilla(nombre: str) -> str:
    return (CARPETA / f"{nombre}.md").read_text(encoding="utf-8")


def _lista_sistemas(sistemas: list) -> str:
    activos = [x for x in sistemas if x.retirado is None]
    if not activos:
        return "- [POR COMPLETAR: el inventario de IA del portal está vacío; añadid los sistemas de IA que usáis]"
    lineas = []
    for x in activos:
        tipo = "IA de nuestro producto" if x.tipo == "producto" else "herramienta de IA de terceros que usa la plantilla"
        para_que = x.campo("para_que").strip()
        lineas.append(f"- **{x.nombre}** ({tipo})" + (f": {para_que}" if para_que else ""))
    return "\n".join(lineas)


def rellenar(texto: str, perfil: dict, sistemas: list, hoy: date) -> str:
    """La plantilla con los datos de la empresa y solo los apartados que le tocan."""
    preguntas = {q.clave: q for q in guia.PREGUNTAS}

    def bloque(m: re.Match) -> str:
        negado, clave, contenido = bool(m.group(1)), m.group(2), m.group(3)
        respuesta = perfil["respuestas"].get(clave, "")
        if respuesta in ("si", "no"):
            return contenido if (respuesta == "no") == negado else ""
        if negado:
            return ""  # «No lo sé»: sale el apartado de «sí», con su aviso
        aviso = f"[POR COMPLETAR: confirmad «{preguntas[clave].texto}»; si no, quitad esto]"
        lineas = contenido.splitlines(keepends=True)
        if lineas and all(l.lstrip().startswith("|") for l in lineas if l.strip()):
            # En una tabla, el aviso va dentro de la primera celda de cada fila
            return "".join(re.sub(r"^(\s*\|\s*)", rf"\1{aviso} ", l, count=1) for l in lineas)
        return f"{aviso}\n{contenido}"

    texto = _BLOQUE.sub(bloque, texto)
    datos = perfil["datos"]
    titulos = {c: t for c, t, _ in guia.DATOS_EMPRESA}
    valores = {c: datos.get(c, "").strip() or f"[POR COMPLETAR: {titulos[c].lower()}]" for c in titulos}
    valores["fecha"] = hoy.strftime("%d/%m/%Y")
    valores["sistemas"] = _lista_sistemas(sistemas)
    texto = _HUECO.sub(lambda m: valores.get(m.group(1), m.group(0)), texto)
    return re.sub(r"(?<!\.)\.\.(?!\.)", ".", texto)  # «Ejemplo, S.L.» al final de una frase no deja «S.L..»


# --- La genérica ---

def puntos_documento(req: guia.Requisito) -> list[guia.Punto]:
    """Los puntos que se demuestran con un documento propio (no los que se cumplen con otro requisito)."""
    return [p for p in req.puntos if p.tipo == "Documento" and not p.apoyos]


# --- Dónde se sube ---

# Lo que cubre un documento son los puntos de documento de los requisitos que lo usan. Además, a mano:
FIRMADO = {"politica-ia": ["5.2.e"]}  # los que cubre una vez aprobado
NOTA = {"no-conformidades": "Es el procedimiento: no cubre ningún punto por sí solo, porque los de la 10.2 piden el "
                            "registro de cada no conformidad (la tabla de su apartado «Registro» sirve para eso). "
                            "Guárdalo en 10.2.a junto con esos registros."}


@dataclass
class Destino:
    cubre: list[str]                 # dónde se sube, también de otros requisitos que usan el mismo documento
    firmado: list[str]               # dónde se sube, además, una vez aprobado
    aparte: list[tuple[str, str]]    # los puntos de este requisito que no cubre, con qué hace falta
    nota: str = ""


def donde(codigo: str) -> Destino:
    """Dónde se sube el borrador de un requisito, una vez completo, y qué puntos suyos no cubre."""
    req = guia.requisito(codigo)
    nombre = PLANTILLAS.get(codigo)
    usan = [guia.requisito(c) for c, n in PLANTILLAS.items() if n == nombre] if nombre else [req]
    cubre = [p.codigo for r in usan for p in puntos_documento(r)]
    firmado = FIRMADO.get(nombre, [])
    aparte = []
    for p in req.puntos:
        if p.codigo in cubre or p.codigo in firmado:
            continue
        if p.apoyos:
            como = f"se marca solo cuando completes {' y '.join(p.apoyos)}; no hace falta subir nada"
        else:
            como = (p.explicacion or p.te_pediran).rstrip(".") or p.tipo.lower()
        aparte.append((p.codigo, como if como[-1] in ".?!»…" else como + "."))
    return Destino(cubre, firmado, aparte, NOTA.get(nombre, ""))


def con_borrador(codigo: str) -> bool:
    req = guia.requisito(codigo)
    return req is not None and (codigo in PLANTILLAS or bool(puntos_documento(req)))


def generica(req: guia.Requisito) -> str:
    """La base para empezar a escribir el documento del requisito, con los huecos de siempre."""
    lineas = [f"# {req.titulo} — {{nombre}}", "",
              "Versión 1.0 · Fecha: {fecha} · Aprobado por: {direccion} · Firma: [POR COMPLETAR: firma de quien aprueba]",
              "", "## Para qué es este documento", "",
              f"Requisito {req.codigo} de la ISO/IEC 42001. {req.llano.pide if req.llano else req.resumen}", ""]
    if req.nota:
        lineas += [f"A tener en cuenta: {req.nota}", ""]
    documentos = puntos_documento(req)
    for p in documentos:
        # Lo que tiene que decir: la explicación en llano, si la hay (si no, el título ya es el texto del punto)
        guia_punto = [x if x[-1] in ".?!»…" else x + "." for x in (p.explicacion, f"El auditor pedirá: {p.te_pediran}" if p.te_pediran
                      else "", "Uno por cada sistema del inventario al que le toque" if p.por_sistema else "") if x]
        lineas += [f"## {p.codigo} — {(p.titulo_llano or p.texto).rstrip('.')}", "",
                   f"[POR COMPLETAR: {' '.join(guia_punto) or 'lo vuestro'}]", ""]
    resto = [p for p in req.puntos if p not in documentos]
    if resto:
        lineas += ["## Lo que no va en este documento", ""]
        for p in resto:
            if p.apoyos:
                como = f"se cumple con {', '.join(p.apoyos)}"
            else:
                como = f"{p.tipo.lower()}" + (f": {p.te_pediran.rstrip('.')}" if p.te_pediran else "")
            lineas.append(f"- **{p.codigo}** {(p.titulo_llano or p.texto).rstrip('.')} ({como}).")
        lineas.append("")
    return "\n".join(lineas)


@dataclass
class Base:
    """El borrador sin IA de un requisito: la estructura fija para la IA y lo que sale sin ella."""
    documento: str      # el documento: el nombre de la plantilla o, en la genérica, el código del requisito
    texto: str
    archivo: str        # el nombre del Word
    aviso: str          # el aviso de arriba si sale sin IA
    requisitos: list    # los requisitos que usan este documento (la política, la 5.2 y la A.2.2)


def base(codigo: str, perfil: dict, sistemas: list, hoy: date) -> Base:
    """El borrador sin IA: su plantilla o, si no tiene, la genérica."""
    if codigo in PLANTILLAS:
        nombre = PLANTILLAS[codigo]
        return Base(nombre, rellenar(plantilla(nombre), perfil, sistemas, hoy),
                    f"{NOMBRES[nombre]} - borrador {hoy.isoformat()}.docx", AVISO,
                    [guia.requisito(c) for c, n in PLANTILLAS.items() if n == nombre])
    req = guia.requisito(codigo)
    titulo = re.sub(r'[\\/:*?"<>|]', "", req.titulo)  # sin caracteres que no valen en un nombre de archivo
    return Base(codigo, rellenar(generica(req), perfil, sistemas, hoy),
                f"{req.codigo} {titulo} - base {hoy.isoformat()}.docx", AVISO_GENERICA, [req])


def documento(codigo: str, perfil: dict, sistemas: list, hoy: date) -> tuple[bytes, str]:
    """El Word del borrador sin IA de un requisito y el nombre del archivo."""
    from portal import word
    b = base(codigo, perfil, sistemas, hoy)
    return word.documento(b.texto, aviso=b.aviso, unir_lineas=True), b.archivo


# --- Con IA ---

ESFUERZO = "medium"
FALTA = "## Lo que falta saber"

INSTRUCCIONES = """Redactas el borrador de un documento del sistema de gestión de la IA (ISO/IEC 42001) de una
empresa. Te paso el requisito que cubre, lo que sabemos de la empresa, su inventario de IA, sus notas y el BORRADOR
BASE: un documento con la estructura fija y huecos [POR COMPLETAR].

Devuelve el documento completo, en español formal y claro, como un documento interno de la empresa listo para revisar.

Reglas:
- La estructura es fija: usa exactamente los mismos títulos del borrador base (las líneas que empiezan por «# » y por
  «## »), con el mismo texto y en el mismo orden. No añadas, quites, cambies ni reordenes títulos.
- Dentro de cada apartado, escribe con lo de la empresa: párrafos, listas con «- » y tablas con «|» como en el base.
  Puedes reescribir y completar el texto del base para que encaje con la empresa.
- Usa solo lo que te paso. No inventes nombres, cifras, fechas, herramientas ni compromisos. Lo que no sepas, déjalo
  así: [POR COMPLETAR: qué falta]. Deja los [POR COMPLETAR] del base que no puedas rellenar (por ejemplo, la firma).
- Si una respuesta dice que algo no existe o no se hace («nadie», «no se revisa», «no tenemos»), no lo cuentes en el
  documento: nada de «actualmente no se hace…». Tampoco escribas que ya existe. Redacta lo que el documento establece y
  deja lo que falta como [POR COMPLETAR: qué hay que decidir].
- Si el documento menciona o se basa en otro documento de la empresa (la política de IA, un procedimiento…), añade
  junto a la primera mención: [A CONFIRMAR: comprobar que «ese documento» está subido y que esto encaja con él]. No
  has leído ese documento: no afirmes lo que dice.
- Las leyes y obligaciones legales que creas que tocan (protección de datos, el Reglamento europeo de IA y su nivel de
  riesgo, las del sector) proponlas marcadas así: [A CONFIRMAR: …], porque es una conclusión legal que alguien tiene
  que revisar.
- Al final, después del último apartado, añade el título «## Lo que falta saber» con una lista «- » de hasta 8
  preguntas concretas a la empresa cuya respuesta te habría permitido completar el documento. No preguntes nada de lo
  que ya aparece en «La empresa» o en «Inventario de IA», aunque esté sin contestar, sin rellenar o en «No lo sé», ni
  con otras palabras: eso se contesta en su formulario, y en el documento se queda como [POR COMPLETAR]. Esta regla
  manda sobre la siguiente. Si necesitas algo que ya está en «Ya preguntado», copia esa pregunta tal cual, sin cambiar
  ni una palabra; no la vuelvas a hacer con otras palabras. Si no falta nada, una sola línea: «- Nada.»
- No escribas nada antes del primer título. Sin negritas fuera de las del base."""


class EstructuraRota(Exception):
    """La IA no ha respetado los títulos del borrador base."""


def _del_formulario(pregunta: str) -> bool:
    """¿Es, con el mismo texto, una pregunta del formulario de «Empresa»? Esa se contesta allí: repetirla dejaría el
    mismo dato en dos sitios (y la Declaración solo mira el formulario)."""
    def normal(t: str) -> str:
        return " ".join(t.split()).rstrip(".").casefold()
    return normal(pregunta) in {normal(q.texto) for q in [*guia.PREGUNTAS, *guia.ABIERTAS]}


def titulos(texto: str) -> list[str]:
    return [" ".join(l.split()) for l in texto.splitlines() if l.startswith("# ") or l.startswith("## ")]


def mensaje(b: Base, perfil: dict, sistemas: list, campos: list[tuple[str, str]], notas: dict[str, str],
            preguntas_ia: list[tuple[str, str]], pendientes: list[str] = ()) -> str:
    """Todo lo que se le da a Claude, en texto. `campos`: los de la ficha de cada sistema (clave, título); `notas`, las
    «Cómo lo hacemos aquí» de los requisitos del documento; `preguntas_ia`, las de la IA ya contestadas; `pendientes`,
    las suyas sin contestar, para que no las repita con otras palabras. Nunca los archivos subidos."""
    partes = ["# El requisito"]
    for req in b.requisitos:
        partes.append(f"{req.codigo} {req.titulo}: {req.llano.pide if req.llano else req.resumen}")
        for p in req.puntos:
            partes.append(f"- {p.codigo} {p.titulo_llano or p.texto}" + (f" (el auditor pedirá: {p.te_pediran})"
                                                                          if p.te_pediran else ""))
    partes.append("\n# La empresa")
    titulos_datos = {c: t for c, t, _ in guia.DATOS_EMPRESA}
    for c, t in titulos_datos.items():
        partes.append(f"- {t}: {perfil['datos'].get(c) or '(sin contestar)'}")
    for q in guia.PREGUNTAS:
        partes.append(f"- {q.texto} {guia.RESPUESTAS.get(perfil['respuestas'].get(q.clave, ''), 'Sin contestar')}")
    for q in perfil.get("visibles", []):
        partes.append(f"- {q.texto} {perfil['abiertas'].get(q.clave) or '(sin contestar)'}")
    for pregunta, respuesta in preguntas_ia:
        partes.append(f"- {pregunta} {respuesta}")
    partes.append("\n# Inventario de IA")
    activos = [x for x in sistemas if x.retirado is None]
    if not activos:
        partes.append("(vacío)")
    for x in activos:
        tipo = "IA de su producto" if x.tipo == "producto" else "herramienta de IA de terceros"
        partes.append(f"## {x.nombre} ({tipo})")
        partes += [f"- {t}: {x.campo(c).strip() or '(sin rellenar)'}" for c, t in campos]
    partes.append("\n# Notas «Cómo lo hacemos aquí»")
    escritas = [f"- {c}: {t.strip()}" for c, t in notas.items() if t and t.strip()]
    partes += escritas or ["(ninguna)"]
    partes.append("\n# Ya preguntado (sin contestar todavía)")
    partes += [f"- {t}" for t in pendientes if not _del_formulario(t)] or ["(nada)"]
    partes += ["\n# BORRADOR BASE (la estructura fija)", b.texto]
    return "\n".join(partes)


def huella(texto_mensaje: str) -> str:
    """Si no cambia nada de lo que se le da a Claude (ni las instrucciones ni el modelo), se reutiliza el anterior."""
    from portal import ia
    return hashlib.sha256(f"{ia.MODELO}\n{INSTRUCCIONES}\n{texto_mensaje}".encode("utf-8")).hexdigest()


def leer(respuesta: str, b: Base) -> tuple[str, list[str]]:
    """El documento de Claude (con «Lo que falta saber» al final) y sus preguntas, sin las que ya están en el formulario
    de «Empresa». Lanza EstructuraRota si los títulos no son los del borrador base."""
    texto = respuesta.strip()
    texto = re.sub(r"^```\w*\n|\n```$", "", texto).strip()  # por si lo envuelve en un bloque de código
    lineas = texto.splitlines()
    corte = next((i for i in range(len(lineas) - 1, -1, -1) if " ".join(lineas[i].split()) == FALTA), None)
    cuerpo = "\n".join(lineas[:corte]) if corte is not None else texto
    if corte is None or titulos(cuerpo) != titulos(b.texto):
        raise EstructuraRota()
    preguntas, repetidas = [], set()
    for i, l in enumerate(lineas[corte + 1:], corte + 1):
        if l.startswith("## "):
            break
        m = re.match(r"^\s*[-*]\s+(.*\S)", l)
        if m and m.group(1).rstrip(".").lower() != "nada":
            if _del_formulario(m.group(1)):
                repetidas.add(i)
            else:
                preguntas.append(m.group(1))
    if repetidas:  # también fuera del Word, para que no salgan allí
        lineas = [l for i, l in enumerate(lineas) if i not in repetidas]
        if not preguntas:
            lineas.insert(corte + 1, "- Nada.")
        texto = "\n".join(lineas)
    return texto, preguntas


def comprobar() -> list[str]:
    """Errores de las plantillas: huecos o preguntas que no existen, apartados sin cerrar, plantillas que faltan."""
    errores = []
    preguntas = {q.clave for q in guia.PREGUNTAS}
    for nombre in sorted(set(PLANTILLAS.values())):
        ruta = CARPETA / f"{nombre}.md"
        if not ruta.exists():
            errores.append(f"falta la plantilla {nombre}.md")
            continue
        texto = ruta.read_text(encoding="utf-8")
        errores += [f"{nombre}: hueco desconocido {{{h}}}" for h in _HUECO.findall(texto) if h not in HUECOS]
        errores += [f"{nombre}: pregunta desconocida «{c}»" for _, c in re.findall(r"^\[si (no )?(\w+)\]", texto, re.M)
                    if c not in preguntas]
        if len(re.findall(r"^\[si ", texto, re.M)) != len(re.findall(r"^\[/si\]", texto, re.M)):
            errores.append(f"{nombre}: un apartado [si …] sin cerrar")
        if re.search(r"^\[si [^\]]*\][^\n]*\n(?:(?!^\[/si\]).)*^\[si ", texto, re.M | re.S):
            errores.append(f"{nombre}: apartados [si …] uno dentro de otro")
    return errores
