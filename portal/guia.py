# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La guía, preparada para las páginas del portal.

Los datos vienen de guia/datos.py (la misma fuente que el Excel). Aquí solo se les da forma:
nombres de campo en vez de posiciones, el «(recomendado)» convertido en etiqueta, y los apoyos
como lista de códigos.
"""
from dataclasses import dataclass, field

from guia import datos

COMO = {"D": "Documento", "R": "Registro", "I": "Inventario", "P": "Práctica", "S": "Resumen"}
CADA_CUANTO = {"Pe": "Periódico", "Ev": "Por evento", "U": "Una vez y revisar"}
POR_SISTEMA = {"Todos": "Una vez por cada IA", "Solo producto": "Solo la IA que ofrecéis a clientes"}
RECOMENDADO = " (recomendado)"


@dataclass
class Punto:
    codigo: str
    texto: str
    tipo: str               # nombre del tipo: Documento, Registro, Inventario, Práctica
    te_pediran: str
    apoyos: list[str]       # códigos de los requisitos en los que se apoya
    recomendado: bool
    por_sistema: str        # "" si no va por sistema
    titulo_llano: str = ""  # la explicación en llano, donde la hay
    explicacion: str = ""


@dataclass
class Llano:
    """Qué pide un requisito, quién lo hace y por dónde empezar, en llano."""
    pide: str
    quien: str
    empezar: str


@dataclass
class Requisito:
    codigo: str
    parte: str              # «Cláusulas 4-10» o «Anexo A»
    bloque: str
    titulo: str
    resumen: str
    obligatorio: bool       # cláusulas: siempre; controles del Anexo A: si aplican
    como: list[str]         # cómo se demuestra
    cada_cuanto: list[str]
    nota: str
    cuando_aplica: str      # solo controles del Anexo A
    puntos: list[Punto] = field(default_factory=list)
    llano: Llano | None = None

    @property
    def es_resumen(self) -> bool:
        return "Resumen" in self.como


def _punto(fila) -> Punto:
    padre, cod, que, tipo, pruebas, apoyo = fila
    recomendado = que.endswith(RECOMENDADO + ".") or que.endswith(RECOMENDADO)
    if recomendado:
        que = que.replace(RECOMENDADO, "")
    return Punto(
        codigo=cod,
        texto=que,
        tipo=COMO[tipo],
        te_pediran=pruebas,
        apoyos=[x.strip() for x in apoyo.split(",") if x.strip()],
        recomendado=recomendado,
        por_sistema=POR_SISTEMA.get(datos.POR_SISTEMA.get(cod, ""), ""),
        titulo_llano=datos.LLANO_PUNTOS.get(cod, ("", ""))[0],
        explicacion=datos.LLANO_PUNTOS.get(cod, ("", ""))[1],
    )


def _cargar() -> dict[str, Requisito]:
    puntos: dict[str, list[Punto]] = {}
    for fila in datos.P:  # ya vienen ordenados como los requisitos
        puntos.setdefault(fila[0], []).append(_punto(fila))
    reqs = {}
    for cod, parte, bloque, tit, res, obl, tipos, _dudoso, nota in datos.filas:
        t = tipos.split()
        reqs[cod] = Requisito(
            codigo=cod,
            parte=parte,
            bloque=bloque,
            titulo=tit,
            resumen=res,
            obligatorio=obl == "Siempre",
            como=[COMO[x] for x in t if x in COMO],
            cada_cuanto=[CADA_CUANTO[x] for x in t if x in CADA_CUANTO],
            nota=nota,
            cuando_aplica=datos.CUANDO.get(cod, ""),
            puntos=puntos.get(cod, []),
            llano=Llano(*datos.LLANO[cod]) if cod in datos.LLANO else None,
        )
    return reqs


REQUISITOS = _cargar()


def requisitos() -> list[Requisito]:
    """Los 65 requisitos, en el orden de la norma."""
    return list(REQUISITOS.values())


def requisito(codigo: str) -> Requisito | None:
    return REQUISITOS.get(codigo)


def por_bloques() -> list[tuple[str, list[tuple[str, list[Requisito]]]]]:
    """Los requisitos agrupados por parte y bloque, para la lista: [(parte, [(bloque, [req…])…])…]."""
    partes: dict[str, dict[str, list[Requisito]]] = {}
    for r in requisitos():
        partes.setdefault(r.parte, {}).setdefault(r.bloque, []).append(r)
    return [(p, list(bloques.items())) for p, bloques in partes.items()]


def punto(codigo: str) -> Punto | None:
    return next((p for r in requisitos() for p in r.puntos if p.codigo == codigo), None)


@dataclass
class Situacion:
    """Algo que ha pasado y reabre varios requisitos a la vez."""
    clave: str
    titulo: str
    cuando: str
    requisitos: list[Requisito]


SITUACIONES = {clave: Situacion(clave, tit, cuando, [REQUISITOS[c] for c in reqs])
               for clave, tit, cuando, reqs in datos.SITUACIONES}

# Lo que pregunta el inventario al dar de alta un sistema
ALTA = Situacion("alta", "Sistema de IA nuevo", "Se ha dado de alta un sistema en el inventario.",
                 [REQUISITOS[c] for c in datos.AL_DAR_DE_ALTA])


def situaciones() -> list[Situacion]:
    return list(SITUACIONES.values())


def situacion(clave: str) -> Situacion | None:
    return SITUACIONES.get(clave)


# --- Buscador (Ctrl K) ---

@dataclass
class Encontrado:
    codigo: str
    titulo: str
    que: str        # «Requisito», «Control del Anexo A» o «Punto de 7.2»
    url: str


def _llano(texto: str) -> str:
    """Sin tildes ni mayúsculas, para que «gestion» encuentre «Gestión»."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def buscar(texto: str, cuantos: int = 12) -> list[Encontrado]:
    """Requisitos y puntos por código o por palabras. Primero lo que encaja por código, luego el título de un
    requisito, luego el de un punto y luego el resto del texto; cada palabra escrita tiene que salir."""
    palabras = _llano(texto).split()
    if not palabras:
        return []
    q = palabras[0]
    res = []
    for r in requisitos():
        que = "Requisito" if r.obligatorio else "Control del Anexo A"
        candidatos = [(True, r.codigo, r.titulo, que, f"/requisitos/{r.codigo}", _llano(r.titulo), _llano(r.resumen))]
        candidatos += [(False, p.codigo, p.texto, f"Punto de {r.codigo}", f"/requisitos/{r.codigo}#{p.codigo}",
                        _llano(p.texto), _llano(p.te_pediran)) for p in r.puntos]
        for es_requisito, codigo, titulo, que_es, url, en_titulo, en_texto in candidatos:
            cod = codigo.lower()
            if len(palabras) == 1 and cod == q:
                orden = 0
            elif len(palabras) == 1 and cod.startswith(q):
                orden = 1 + len(cod)  # los más cortos (el requisito) antes que sus puntos
            elif all(w in en_titulo for w in palabras):
                orden = 100 if es_requisito else 150
            elif all(w in en_titulo or w in en_texto for w in palabras):
                orden = 200
            else:
                continue
            res.append((orden, len(res), Encontrado(codigo, titulo, que_es, url)))
    return [e for _, _, e in sorted(res)[:cuantos]]


# --- Cuestionario de la empresa ---

@dataclass
class Pregunta:
    clave: str
    texto: str
    controles: list[str]   # los controles del Anexo A que decide


PREGUNTAS = [Pregunta(c, t, list(ctrl)) for c, t, ctrl in datos.PREGUNTAS]
CASI_SIEMPRE = list(datos.CASI_SIEMPRE)
DATOS_EMPRESA = list(datos.DATOS_EMPRESA)  # (clave, qué se pregunta, ejemplo)
RESPUESTAS = {"si": "Sí", "no": "No", "nose": "No lo sé"}


@dataclass
class Abierta:
    """Una pregunta abierta del cuestionario: se contesta en llano."""
    bloque: int
    clave: str
    texto: str
    ejemplo: str
    requisitos: list[Requisito]   # los que se proponen reabrir si cambia la respuesta


BLOQUES = dict(datos.BLOQUES)
SOLO_SI_DESARROLLA = datos.SOLO_SI_DESARROLLA
ABIERTAS = [Abierta(b, c, t, ej, [REQUISITOS[r] for r in reqs]) for b, c, t, ej, reqs in datos.ABIERTAS]


def abiertas(desarrolla: str) -> list[Abierta]:
    """Las que salen: las del bloque 5 solo si la empresa no ha dicho que no desarrolla IA."""
    return [q for q in ABIERTAS if q.bloque != SOLO_SI_DESARROLLA or desarrolla != "no"]
