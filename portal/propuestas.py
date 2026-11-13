# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La ayuda con la Declaración.

Claude propone, para cada control del Anexo A, si aplica a la empresa: APLICA, NO APLICA o FALTA SABER, con el porqué
ya redactado y en qué se apoya. Lo que se le da: el cuestionario de la empresa, su inventario y el «¿Aplica a tu
empresa?» de cada control. Contesta con una línea por control y una forma fija; lo que no encaje se descarta, nunca se
adivina. No decide nada: las propuestas se aceptan, se cambian o se descartan en la Declaración.

Declaración mixta: los controles claros los decide el portal, sin IA y siempre igual, con las respuestas
Sí / No del cuestionario (`fijas`). Claude decide solo los dudosos, redacta el porqué de todos y avisa si algo no cuadra;
si en uno ya decidido dice otra cosa, se queda la del portal.
"""
import re
from dataclasses import dataclass

from portal import guia

APLICA, NO_APLICA, FALTA = "aplica", "no_aplica", "falta"
PORTAL, IA = "portal", "ia"  # quién ha decidido la propuesta
CASI_SIEMPRE = "aplica casi siempre"
ETIQUETA = {"APLICA": APLICA, "NO APLICA": NO_APLICA, "FALTA SABER": FALTA}
ESFUERZO = "medium"

INSTRUCCIONES = """Ayudas a una empresa a preparar su Declaración de Aplicabilidad de la ISO/IEC 42001: decidir, para
cada control del Anexo A, si aplica a la empresa y por qué.

Te paso lo que se sabe de la empresa (sus respuestas a un cuestionario y su inventario de sistemas de IA) y una lista
de controles, cada uno con cuándo suele aplicar y de qué pregunta del cuestionario depende.

Algunos controles ya vienen decididos por las respuestas de la empresa («Ya decidido: …»): en esos, pon esa misma
decisión y redacta solo el porqué. Los que dicen «Decide tú», los decides tú.

Para cada control de la lista, responde con UNA línea, exactamente con esta forma:
CÓDIGO | DECISIÓN | PORQUÉ | SE APOYA EN | AVISO

- DECISIÓN es APLICA, NO APLICA o FALTA SABER.
- PORQUÉ: una o dos frases para la Declaración, sobre la empresa y en tercera persona («La empresa no entrena
  modelos con datos propios: usa modelos de terceros ya entrenados»). Si la decisión es FALTA SABER, en su lugar
  escribe la pregunta concreta que habría que hacerle a la empresa.
- SE APOYA EN: en qué te basas, corto: «pregunta 2», «inventario: ChatGPT (herramienta)», «aplica casi siempre».
- AVISO: casi siempre vacío. Solo si el inventario contradice una respuesta del cuestionario (por ejemplo, «No» a si
  desarrollan IA y un sistema que es IA del producto), una frase que lo diga para que la empresa lo mire.
- No uses el carácter «|» dentro de los textos.

Reglas:
- Básate solo en lo que te paso. No inventes nada de la empresa.
- Si la respuesta que decide el control es «No lo sé» o no está contestada, y el inventario tampoco lo aclara, la
  decisión es FALTA SABER.
- Los controles que aplican casi siempre son APLICA salvo que lo que te paso diga claramente lo contrario.
- Escribe en español, en llano.
- No escribas nada más que las líneas: ni introducción, ni conclusión."""


@dataclass
class Propuesta:
    control: str
    decision: str      # APLICA, NO_APLICA o FALTA
    porque: str        # o la pregunta, si falta saber
    apoyo: str         # en qué se basa; en las del portal, «pregunta N» o «aplica casi siempre»
    aviso: str = ""    # si algo no cuadra (el inventario contradice una respuesta)
    quien: str = IA    # PORTAL o IA


def _preguntas_de(control: str) -> list:
    """Las preguntas del cuestionario que deciden un control, con su número (casi siempre una; el A.8.3, dos)."""
    return [(n, q) for n, q in enumerate(guia.PREGUNTAS, 1) if control in q.controles]


def _numeros(preguntas: list) -> str:
    ns = [str(n) for n, _ in preguntas]
    return f"pregunta {ns[0]}" if len(ns) == 1 else f"preguntas {', '.join(ns[:-1])} y {ns[-1]}"


def fijas(perfil: dict, sistemas: list) -> dict[str, Propuesta]:
    """Los controles que decide el portal, sin IA y siempre igual (docs/v3.md, Declaración mixta):
    - aplica casi siempre → APLICA;
    - alguna de sus preguntas en «Sí» → APLICA; todas en «No» → NO APLICA;
    - en «No lo sé» o sin contestar, con el inventario vacío → FALTA SABER, con la pregunta del cuestionario.
    El resto (dudosas con sistemas en el inventario, que pueden aclararlo) no sale: lo decide Claude.
    El porqué es uno sencillo, por si Claude no está; normalmente lo redacta Claude."""
    hay_sistemas = any(x.retirado is None for x in sistemas)
    res = {}
    for codigo in controles():
        if codigo in guia.CASI_SIEMPRE:
            r = guia.requisito(codigo)
            res[codigo] = Propuesta(codigo, APLICA, r.cuando_aplica or "Aplica a casi cualquier empresa.", CASI_SIEMPRE,
                                    quien=PORTAL)
            continue
        suyas = _preguntas_de(codigo)
        respuestas = [(n, q, perfil["respuestas"].get(q.clave, "")) for n, q in suyas]
        si = [(n, q) for n, q, v in respuestas if v == "si"]
        if si:
            n, q = si[0]
            res[codigo] = Propuesta(codigo, APLICA, f"Según el cuestionario: «{q.texto}» Sí.", f"pregunta {n}",
                                    quien=PORTAL)
        elif all(v == "no" for _, _, v in respuestas):
            textos = " ".join(f"«{q.texto}» No." for _, q in suyas)
            res[codigo] = Propuesta(codigo, NO_APLICA, f"Según el cuestionario: {textos}", _numeros(suyas),
                                    quien=PORTAL)
        elif not hay_sistemas:
            dudosas = [(n, q) for n, q, v in respuestas if v != "no"]
            res[codigo] = Propuesta(codigo, FALTA, " ".join(q.texto for _, q in dudosas), _numeros(dudosas),
                                    quien=PORTAL)
    return res


def combinar(fijas_: dict[str, Propuesta], leidas: dict[str, Propuesta], controles_: list[str]) -> dict[str, Propuesta]:
    """Las propuestas que se guardan: en las del portal manda su decisión y, si Claude está de acuerdo, se queda con su
    porqué (mejor redactado) y su aviso; si dice otra cosa, se avisa. Las demás, las de Claude tal cual."""
    res = {}
    for c in controles_:
        f, l = fijas_.get(c), leidas.get(c)
        if f is None:
            if l is not None:
                res[c] = Propuesta(c, l.decision, l.porque, l.apoyo, l.aviso, IA)
            continue
        porque, aviso = f.porque, ""
        if l is not None:
            if l.decision == f.decision:
                porque, aviso = l.porque, l.aviso
            else:
                aviso = l.aviso or f"La IA habría dicho otra cosa: {l.porque}"
        res[c] = Propuesta(c, f.decision, porque, f.apoyo, aviso, PORTAL)
    return res


def quien_decide(quien: str, apoyo: str) -> str:
    """Lo que se enseña en la Declaración y en «Actividad»: quién ha decidido la propuesta."""
    if quien != PORTAL:
        return "propuesta de la IA"
    if apoyo == CASI_SIEMPRE:
        return CASI_SIEMPRE
    return f"según tu respuesta a la {apoyo}"


def _respuesta(perfil: dict, clave: str) -> str:
    valor = perfil["respuestas"].get(clave, "")
    return guia.RESPUESTAS.get(valor, "Sin contestar")


def mensaje(perfil: dict, sistemas: list, controles: list[str], aclaraciones: dict[str, tuple[str, str]] | None = None,
            fijas_: dict[str, Propuesta] | None = None) -> str:
    """Lo que se le da a Claude: la empresa, su inventario y los controles a proponer. `aclaraciones`: para un control
    que estaba en FALTA SABER, la pregunta que se hizo y lo que contestó la persona. `fijas_`: los que ya ha decidido
    el portal; los demás, «Decide tú»."""
    preguntas = list(enumerate(guia.PREGUNTAS, 1))
    decide = {c: n for n, q in preguntas for c in q.controles}
    lineas = ["# La empresa", ""]
    for clave, titulo, _ in guia.DATOS_EMPRESA:
        lineas.append(f"- {titulo}: {perfil['datos'].get(clave) or 'Sin contestar'}")
    lineas += ["", "## Cuestionario", ""]
    for n, q in preguntas:
        lineas.append(f"{n}. {q.texto} → {_respuesta(perfil, q.clave)}")
    lineas += ["", "## Inventario de sistemas de IA", ""]
    activos = [x for x in sistemas if x.retirado is None]
    if not activos:
        lineas.append("(vacío: aún no se ha dado de alta ningún sistema)")
    for x in activos:
        tipo = "IA del producto" if x.tipo == "producto" else "herramienta de uso (de terceros)"
        lineas.append(f"- {x.nombre} ({tipo})")
        for campo in ("para_que", "datos", "herramientas", "infraestructura", "personas"):
            if x.campo(campo).strip():
                lineas.append(f"  - {campo.replace('_', ' ')}: {x.campo(campo).strip()}")
    lineas += ["", "# Controles", ""]
    for codigo in controles:
        r = guia.requisito(codigo)
        de_que = (f"depende de la pregunta {decide[codigo]}" if codigo in decide else "aplica casi siempre")
        lineas.append(f"- {codigo} {r.titulo} ({de_que}). Cuándo aplica: {r.cuando_aplica}")
        if fijas_ is not None:
            f = fijas_.get(codigo)
            lineas.append(f"  - Ya decidido: {_NOMBRE[f.decision]} ({f.apoyo})" if f else "  - Decide tú")
        if aclaraciones and codigo in aclaraciones:
            pregunta, contestado = aclaraciones[codigo]
            lineas.append(f"  - Se le preguntó a la empresa: «{pregunta}». Contestó: «{contestado}»")
    return "\n".join(lineas)


_NOMBRE = {v: k for k, v in ETIQUETA.items()}
_LINEA = re.compile(r"^\W*(A\.\d+(?:\.\d+)+)\s*\|\s*(APLICA|NO APLICA|FALTA SABER)\s*\|\s*(.+?)\s*\|\s*([^|]*?)\s*"
                    r"(?:\|\s*(.*?)\s*)?$", re.I)


def leer(texto: str, controles: list[str]) -> dict[str, Propuesta]:
    """Las propuestas de la respuesta de Claude. Solo valen las líneas con la forma pedida y de un control que se le
    pidió; si un control sale dos veces, vale la primera. Los que falten no tienen propuesta."""
    pedidos, res = set(controles), {}
    for linea in texto.splitlines():
        m = _LINEA.match(linea.strip().strip("*"))
        if not m:
            continue
        codigo, decision, porque, apoyo, aviso = m.groups()
        if codigo in pedidos and codigo not in res and porque.strip():
            res[codigo] = Propuesta(codigo, ETIQUETA[decision.upper()], porque.strip(), apoyo.strip(),
                                    (aviso or "").strip())
    return res


def controles() -> list[str]:
    """Los 38 controles del Anexo A, en orden."""
    return [r.codigo for r in guia.requisitos() if not r.obligatorio]
