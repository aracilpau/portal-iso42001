# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La conexión del portal con Claude.

El portal lanza el programa `claude` (Claude Code) de este ordenador, que usa la sesión, es decir la suscripción, de
quien usa el portal. No hace falta ninguna librería: es lo mismo que hace por dentro el Claude Agent SDK, y para una
pregunta con una respuesta basta. Claude va aislado: sin ninguna herramienta, sin la configuración ni los MCP del
usuario; solo ve lo que le da cada pieza. Si no está disponible o falla, se lanza `ClaudeNoDisponible` con un mensaje
para la persona, y el resto del portal sigue igual.
"""
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

MODELO = "claude-opus-5-5"  # Opus 5.5 en todas las piezas, con el ID explícito
ESPERA = 300                # segundos como mucho; después se da por fallida


class ClaudeNoDisponible(Exception):
    """Claude Code no está, no tiene sesión o ha fallado. El texto es para enseñárselo a la persona."""


def programa() -> str | None:
    return shutil.which("claude")


def disponible() -> bool:
    return programa() is not None


def entorno() -> dict[str, str]:
    """El entorno de Claude, sin claves de API: si llegara una, se cobraría por API sin avisar."""
    return {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}


def argumentos(instrucciones: Path, esfuerzo: str, con_imagenes: bool = False) -> list[str]:
    """Cómo se lanza: una respuesta y fuera, con el modelo y el esfuerzo de la pieza, sin herramientas ni la
    configuración del usuario, y sin guardar la conversación. Con imágenes, el mensaje va en «stream-json»."""
    formato = (["--input-format", "stream-json", "--output-format", "stream-json", "--verbose"] if con_imagenes
               else ["--output-format", "json"])
    return ["-p", *formato, "--model", MODELO, "--effort", esfuerzo,
            "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
            # Las instrucciones van en un archivo: en Windows, largas, rompen la línea de comandos (lo vio AI-PM)
            "--system-prompt-file", str(instrucciones)]


def entrada(mensaje: str, imagenes: list[tuple[str, str]] | None) -> bytes:
    """Lo que se le escribe a Claude: el mensaje tal cual o, con imágenes, una línea «stream-json» con las imágenes
    (tipo, base64) delante del texto."""
    if not imagenes:
        return mensaje.encode("utf-8")
    partes = [{"type": "image", "source": {"type": "base64", "media_type": t, "data": d}} for t, d in imagenes]
    partes.append({"type": "text", "text": mensaje})
    return (json.dumps({"type": "user", "message": {"role": "user", "content": partes}}) + "\n").encode("utf-8")


async def tarea(nombre: str, instrucciones: str, mensaje: str, esfuerzo: str = "medium",
                imagenes: list[tuple[str, str]] | None = None) -> str:
    """Pregunta una vez y devuelve el texto de la respuesta. Lanza ClaudeNoDisponible si no se puede."""
    ruta = programa()
    if ruta is None:
        raise ClaudeNoDisponible("Claude no está disponible: no se encuentra Claude Code en este ordenador.")
    archivo = Path(tempfile.gettempdir()) / f"portal_iso_{nombre}.txt"
    archivo.write_text(instrucciones, encoding="utf-8")
    try:
        # En un hilo aparte: funciona igual sea cual sea el bucle de eventos del servidor en Windows
        hecho = await asyncio.to_thread(
            subprocess.run, [ruta, *argumentos(archivo, esfuerzo, bool(imagenes))], input=entrada(mensaje, imagenes),
            capture_output=True, env=entorno(), timeout=ESPERA)
        salida = hecho.stdout
    except subprocess.TimeoutExpired:
        raise ClaudeNoDisponible("Claude está tardando demasiado. Vuelve a probar en un momento.")
    except OSError as e:
        raise ClaudeNoDisponible(f"No se ha podido lanzar Claude Code ({e}).") from e
    return leer_respuesta(salida.decode("utf-8", errors="replace"))


def leer_respuesta(salida: str) -> str:
    """El texto de la respuesta, de lo que devuelve `claude -p`: un JSON o, en «stream-json», una línea por evento
    de las que vale la última de tipo «result»."""
    try:
        lineas = [json.loads(l) for l in salida.splitlines() if l.strip()]
        resultados = [l for l in lineas if isinstance(l, dict) and l.get("type") == "result"]
        datos = resultados[-1] if resultados else (lineas[0] if len(lineas) == 1 else None)
        if not isinstance(datos, dict):
            raise json.JSONDecodeError("sin resultado", salida, 0)
    except json.JSONDecodeError:
        raise ClaudeNoDisponible("Claude no ha respondido bien. Comprueba que Claude Code tiene la sesión iniciada "
                                 "(abre Claude Code una vez) y vuelve a probar.")
    if datos.get("is_error"):
        raise ClaudeNoDisponible("Claude ha devuelto un error. Comprueba que Claude Code tiene la sesión iniciada "
                                 "y vuelve a probar.")
    texto = (datos.get("result") or "").strip()
    if not texto:
        raise ClaudeNoDisponible("Claude no ha devuelto nada. Vuelve a probar en un momento.")
    return texto
