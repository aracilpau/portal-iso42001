# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El chat («Preguntar»).

Claude conversa sobre la norma y sobre el portal. Siempre tiene delante el índice de la guía (cada requisito con su
resumen de una línea y en cuáles se apoya) y el del manual de uso; el detalle lo lee con herramientas cuando le hace
falta, igual que el estado del espacio. Solo lee: ninguna herramienta cambia nada.

Es la única pieza que usa el Claude Agent SDK: una conversación necesita herramientas, recordar lo anterior y
que la respuesta vaya saliendo y se pueda parar. Las conversaciones viven en memoria: se pierden al cerrar el portal.
"""
import asyncio
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Callable

from portal import guia, ia

ESFUERZO = "low"  # que responda rápido
MANUAL = Path(__file__).resolve().parent.parent / "docs" / "manual.md"


# --- Lo que sabe siempre: los índices ---

def secciones_manual() -> dict[str, str]:
    """El manual por pantallas: «## clave» → su texto."""
    texto = MANUAL.read_text(encoding="utf-8") if MANUAL.exists() else ""
    partes = re.split(r"^## (\S+)\s*$", texto, flags=re.M)
    return {partes[i]: partes[i + 1].strip().strip("-").strip() for i in range(1, len(partes) - 1, 2)
            if partes[i] != "Índice"}


def indice_manual() -> str:
    texto = MANUAL.read_text(encoding="utf-8") if MANUAL.exists() else ""
    m = re.search(r"^## Índice\s*$(.*?)^---", texto, flags=re.M | re.S)
    return m.group(1).strip() if m else ""


def indice_guia() -> str:
    """Cada requisito en una línea: código, título, resumen, si es control y en cuáles se apoyan sus puntos."""
    lineas = []
    for r in guia.requisitos():
        apoyos = sorted({a for p in r.puntos for a in p.apoyos})
        que = "" if r.obligatorio else " [control del Anexo A]"
        se_apoya = f" (se apoya en {', '.join(apoyos)})" if apoyos else ""
        lineas.append(f"- {r.codigo} {r.titulo}{que}: {r.resumen}{se_apoya}")
    return "\n".join(lineas)


INSTRUCCIONES = """Eres el asistente del portal de una empresa que se está certificando en la ISO/IEC 42001 (sistemas de
gestión de la IA). Respondes preguntas sobre la norma (qué pide cada requisito, qué hay que entregar, qué pedirá el
auditor) y sobre cómo se usa el portal.

Cómo respondes:
- En español, en llano, breve: lo que se pregunta, sin rodeos. Usa listas cortas si ayudan.
- Cada vez que nombres un requisito o un punto, enlázalo así: [7.2](/requisitos/7.2) o [7.2.a](/requisitos/7.2#7.2.a).
- Básate en la guía, el manual y el estado del espacio, que consultas con tus herramientas. Antes de detallar un
  requisito, léelo con leer_requisito; antes de explicar cómo se hace algo en el portal, lee su pantalla con
  leer_manual. Si no lo sabes o no está, dilo: no inventes.
- No copies el texto de la norma: explica con las palabras de la guía.
- Solo consultas: no puedes marcar, subir, decidir ni cambiar nada. Si te lo piden, explica cómo hacerlo en el portal
  y enlaza la página.
- Con cada pregunta te digo en qué página está la persona: úsalo para entender a qué se refiere («esto», «aquí»).

# Índice de la guía (65 requisitos; el detalle, con leer_requisito)

{guia}

# Índice del manual de uso (cada pantalla, con leer_manual)

{manual}"""


def instrucciones() -> str:
    return INSTRUCCIONES.format(guia=indice_guia(), manual=indice_manual())


def detalle_requisito(codigo: str) -> str:
    """Todo lo de la guía sobre un requisito: puntos, «Te pedirán», en qué se apoya, cuándo aplica."""
    r = guia.requisito(codigo.strip())
    if r is None:
        return f"No hay ningún requisito «{codigo}». Los códigos están en el índice de la guía."
    lineas = [f"{r.codigo} {r.titulo} ({r.bloque}; {'obligatorio' if r.obligatorio else 'control del Anexo A'})",
              f"Qué es: {r.resumen}",
              f"Cómo se demuestra: {', '.join(r.como)}. Cada cuánto: {', '.join(r.cada_cuanto)}."]
    if r.nota:
        lineas.append(f"A tener en cuenta: {r.nota}")
    if r.cuando_aplica:
        lineas.append(f"¿Aplica a tu empresa?: {r.cuando_aplica}")
    for p in r.puntos:
        extra = [p.tipo] + (["recomendado"] if p.recomendado else []) + ([p.por_sistema] if p.por_sistema else [])
        lineas.append(f"\n{p.codigo} ({', '.join(extra)}): {p.texto}")
        if p.te_pediran:
            lineas.append(f"  Te pedirán: {p.te_pediran}")
        if p.apoyos:
            lineas.append(f"  Se apoya en: {', '.join(p.apoyos)} (se cumple solo cuando estén completos)")
    return "\n".join(lineas)


# --- Las herramientas (todas de solo lectura) ---

@dataclass
class Consultas:
    """Lo que el chat puede consultar del espacio; lo pone el portal (main.py). Cada función devuelve texto."""
    estado_requisito: Callable[[str], str]
    lo_siguiente: Callable[[], str]
    inventario: Callable[[], str]
    declaracion: Callable[[], str]
    cuestionario: Callable[[], str]


def herramientas(consultas: Consultas):
    """El servidor de herramientas del chat, dentro del propio portal, y los nombres para permitirlas."""
    from claude_agent_sdk import create_sdk_mcp_server, tool

    def texto(t: str) -> dict:
        return {"content": [{"type": "text", "text": t}]}

    @tool("leer_requisito", "Lo que dice la guía de un requisito: puntos, «Te pedirán», en qué se apoya, cuándo aplica.",
          {"codigo": str})
    async def leer_requisito(args):
        return texto(detalle_requisito(args.get("codigo", "")))

    @tool("leer_manual", "Cómo se usa una pantalla o parte del portal. «pantalla» es una clave del índice del manual.",
          {"pantalla": str})
    async def leer_manual(args):
        secciones = secciones_manual()
        clave = args.get("pantalla", "").strip().lower()
        return texto(secciones.get(clave) or f"No hay «{clave}» en el manual. Claves: {', '.join(secciones)}")

    @tool("estado_requisito", "El estado de un requisito en este espacio: qué puntos están cumplidos, cuándo vencen, "
          "los nombres de sus archivos, la nota «Cómo lo hacemos aquí» y si aplica.", {"codigo": str})
    async def estado_requisito(args):
        return texto(consultas.estado_requisito(args.get("codigo", "").strip()))

    @tool("lo_siguiente", "Lo pendiente del espacio: vencidos, lo que vence pronto, recordatorios y el avance general.", {})
    async def lo_siguiente(args):
        return texto(consultas.lo_siguiente())

    @tool("inventario", "Los sistemas de IA del inventario, con su tipo y su ficha.", {})
    async def inventario(args):
        return texto(consultas.inventario())

    @tool("declaracion", "La Declaración de Aplicabilidad: qué controles aplican, cuáles no y por qué, y cuáles faltan.", {})
    async def declaracion(args):
        return texto(consultas.declaracion())

    @tool("cuestionario", "Los datos generales de la empresa y sus respuestas al cuestionario.", {})
    async def cuestionario(args):
        return texto(consultas.cuestionario())

    todas = [leer_requisito, leer_manual, estado_requisito, lo_siguiente, inventario, declaracion, cuestionario]
    servidor = create_sdk_mcp_server(name="portal", version="1.0.0", tools=todas)
    return servidor, [f"mcp__portal__{t.name}" for t in todas]


def opciones(consultas: Consultas):
    """Claude para el chat: Opus 5.5, esfuerzo bajo, solo nuestras herramientas (ninguna de Claude Code), sin la
    configuración ni los MCP del usuario, y con la respuesta a trozos."""
    from claude_agent_sdk import ClaudeAgentOptions
    servidor, nombres = herramientas(consultas)
    archivo = Path(tempfile.gettempdir()) / "portal_iso_chat.txt"
    archivo.write_text(instrucciones(), encoding="utf-8")
    return ClaudeAgentOptions(
        model=ia.MODELO,
        effort=ESFUERZO,
        system_prompt={"type": "file", "path": str(archivo)},  # en Windows, largas, rompen la línea de comandos
        tools=[],                       # ninguna herramienta de Claude Code
        mcp_servers={"portal": servidor},
        allowed_tools=nombres,          # solo las nuestras, todas de solo lectura
        permission_mode="bypassPermissions",
        strict_mcp_config=True,
        setting_sources=[],
        include_partial_messages=True,  # la respuesta va saliendo
    )


# --- Las conversaciones ---

QUE_CONSULTA = {"leer_requisito": "Leyendo la guía", "leer_manual": "Mirando el manual",
                "estado_requisito": "Mirando tu espacio", "lo_siguiente": "Mirando lo pendiente",
                "inventario": "Mirando el inventario", "declaracion": "Mirando la Declaración",
                "cuestionario": "Mirando el cuestionario"}


@dataclass
class Conversacion:
    """Una conversación del panel. Un Claude abierto mientras dure; se cierra al empezar otra o al cerrar el portal."""
    consultas: Consultas
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cliente: object = None
    ocupada: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def abrir(self):
        if not ia.disponible():
            raise ia.ClaudeNoDisponible("Claude no está disponible: no se encuentra Claude Code en este ordenador.")
        for clave in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):  # que use la suscripción, no la API
            os.environ.pop(clave, None)
        from claude_agent_sdk import ClaudeSDKClient
        self.cliente = ClaudeSDKClient(options=opciones(self.consultas))
        await self.cliente.connect()

    async def preguntar(self, pregunta: str, pagina: str) -> AsyncIterator[dict]:
        """Va dando la respuesta a trozos: {"texto": …} y, mientras consulta algo, {"consulta": …}."""
        from claude_agent_sdk import AssistantMessage, ClaudeSDKError, ResultMessage, StreamEvent, TextBlock
        async with self.ocupada:
            try:
                if self.cliente is None:
                    await self.abrir()
                await self.cliente.query(f"[La persona está en: {pagina}]\n\n{pregunta}")
                escrito = False
                async for m in self.cliente.receive_response():
                    if isinstance(m, StreamEvent):
                        e = m.event
                        if e.get("type") == "content_block_delta" and e.get("delta", {}).get("type") == "text_delta":
                            escrito = True
                            yield {"texto": e["delta"]["text"]}
                        elif e.get("type") == "content_block_start" and e.get("content_block", {}).get("type") == "tool_use":
                            nombre = e["content_block"].get("name", "").rsplit("__", 1)[-1]
                            yield {"consulta": QUE_CONSULTA.get(nombre, "Consultando")}
                    elif isinstance(m, AssistantMessage) and not escrito:
                        # Por si no llegan los trozos: el texto entero de una vez
                        for b in m.content:
                            if isinstance(b, TextBlock):
                                yield {"texto": b.text}
                    elif isinstance(m, ResultMessage) and m.is_error:
                        yield {"error": "Claude ha devuelto un error. Vuelve a probar."}
            except ia.ClaudeNoDisponible as e:
                yield {"error": str(e)}
            except ClaudeSDKError:
                await self.cerrar()
                yield {"error": "Claude no ha podido responder. Comprueba que Claude Code tiene la sesión iniciada."}

    async def parar(self):
        if self.cliente is not None:
            try:
                await self.cliente.interrupt()
            except Exception:
                pass

    async def cerrar(self):
        cliente, self.cliente = self.cliente, None
        if cliente is not None:
            try:
                await cliente.disconnect()
            except Exception:
                pass
