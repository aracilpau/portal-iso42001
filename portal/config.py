# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Dónde guarda el portal sus datos.

Es el único sitio que cambia al pasar de la versión local a la web: aquí se decide dónde
están los datos.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# arrancar.bat pide el portal instalado: el modo (solo en este ordenador o compartido con el MySQL) sale
# de los ajustes de este ordenador y, si aún no hay, se ve la instalación. Sin eso (arrancar-local.bat, el portal de
# prueba, las pruebas automáticas), todo va en el ordenador, con SQLite, en la carpeta `datos` del programa.
INSTALADO = os.environ.get("PORTAL_INSTALADO") == "1"
# El MySQL sin pasar por los ajustes: lo usaba arrancar.bat en versiones anteriores
SERVIDOR = os.environ.get("PORTAL_SERVIDOR") == "1"

# Los ajustes de este ordenador: en la carpeta de ajustes del usuario en Windows (AppData), fuera del programa, para que
# actualizar el programa no los toque. Se puede cambiar con la variable PORTAL_AJUSTES (las pruebas automáticas
# usan una carpeta temporal).
AJUSTES = Path(os.environ.get("PORTAL_AJUSTES") or
               Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Portal ISO 42001") / "ajustes.json"

# La clave del MySQL: fuera de git (regla 3 de datos). La escribe la instalación al lado de los ajustes;
# antes se pasaba en mano y se dejaba en la carpeta del programa, donde se sigue buscando si no está la otra.
# (PORTAL_SECRETOS_PROGRAMA lo cambia, para probar una instalación desde cero en un ordenador que ya tiene el portal)
SECRETOS_PROGRAMA = Path(os.environ.get("PORTAL_SECRETOS_PROGRAMA") or RAIZ / "secretos.env")


def secretos_de(ajustes: Path) -> Path:
    return ajustes.parent / "secretos.env"


SECRETOS = secretos_de(AJUSTES) if secretos_de(AJUSTES).exists() else SECRETOS_PROGRAMA

# Carpeta de datos: fuera de git (regla 1 de datos). Se puede cambiar con la variable PORTAL_DATOS.
# En local, dentro van `cuentas.db` (quién entra y en qué empresas) y una carpeta por empresa con su `portal.db` y sus
# `pruebas/`. Con el MySQL, los datos están en el servidor y las pruebas en la carpeta elegida
# (abajo); `datos-servidor/` es solo la carpeta de referencia de las empresas, aparte de la de local.
DATOS_LOCAL, DATOS_SERVIDOR = RAIZ / "datos", RAIZ / "datos-servidor"
DATOS = Path(os.environ.get("PORTAL_DATOS", DATOS_SERVIDOR if SERVIDOR else DATOS_LOCAL))

# Portal de prueba (arrancar-prueba.bat): lo dice en la cabecera para no confundirlo con el de verdad
PRUEBA = os.environ.get("PORTAL_PRUEBA") == "1"

# Las pruebas del portal compartido van en la carpeta que elige cada uno: una de Teams o SharePoint
# sincronizada con OneDrive, una de red… Cada ordenador apunta la suya en sus ajustes.


class CarpetaNoVale(ValueError):
    """La carpeta elegida no sirve; el mensaje dice por qué, en llano."""


def leer_ajustes(ajustes: Path = AJUSTES) -> dict:
    try:
        datos = json.loads(ajustes.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def carpeta_elegida(ajustes: Path = AJUSTES) -> Path | None:
    """La carpeta apuntada en los ajustes, exista o no (para decir cuál era si ya no está)."""
    ruta = leer_ajustes(ajustes).get("carpeta")
    return Path(ruta) if isinstance(ruta, str) and ruta else None


def carpeta_pruebas(ajustes: Path = AJUSTES) -> Path | None:
    """La carpeta de las pruebas en este ordenador, o None si no se ha elegido o ya no está (el portal la pide)."""
    ruta = carpeta_elegida(ajustes)
    try:
        return ruta if ruta is not None and ruta.is_dir() else None
    except OSError:
        return None


def comprobar_carpeta(texto: str) -> Path:
    """La carpeta escrita o pegada, si sirve: que exista y se pueda escribir en ella. Si no, CarpetaNoVale."""
    texto = texto.strip().strip('"').strip()
    if not texto:
        raise CarpetaNoVale("Elige una carpeta con «Examinar» o pega su ruta.")
    ruta = Path(os.path.expandvars(texto)).expanduser()
    if not ruta.is_absolute():
        raise CarpetaNoVale(f"«{texto}» no es una ruta completa. Tiene que empezar por la unidad, como C:\\…, o por \\\\ "
                            "si es una carpeta de red. Lo más fácil es usar «Examinar».")
    try:
        if not ruta.is_dir():
            raise CarpetaNoVale(f"No se encuentra la carpeta «{ruta}» en este ordenador. Comprueba que existe "
                                "(y, si es de Teams o SharePoint, que está sincronizada).")
        prueba = ruta / ".portal-prueba"
        prueba.write_text("", encoding="utf-8")
        prueba.unlink()
    except CarpetaNoVale:
        raise
    except OSError:
        raise CarpetaNoVale(f"No se puede guardar nada en «{ruta}»: este usuario no tiene permiso para escribir ahí. "
                            "Elige otra o pide permiso.")
    return ruta


def guardar_carpeta(texto: str, ajustes: Path = AJUSTES) -> Path:
    """Comprueba la carpeta y la apunta en los ajustes de este ordenador, sin tocar lo demás que haya."""
    ruta = comprobar_carpeta(texto)
    datos = leer_ajustes(ajustes)
    datos["carpeta"] = str(ruta)
    ajustes.parent.mkdir(parents=True, exist_ok=True)
    ajustes.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def examinar(inicial: Path | None = None) -> str | None:
    """Abre la ventana de Windows para elegir una carpeta y devuelve la elegida, o None si se cancela. Va en un
    programa aparte (tkinter, que viene con Python), para no bloquear el portal ni depender de su hilo."""
    guion = ("import sys, tkinter\n"
             "from tkinter import filedialog\n"
             "r = tkinter.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
             "c = filedialog.askdirectory(parent=r, title='Carpeta de los archivos de pruebas', mustexist=True, "
             "initialdir=sys.argv[1] or None)\n"
             "sys.stdout.buffer.write((c or '').encode('utf-8'))")
    try:
        hecho = subprocess.run([sys.executable, "-c", guion, str(inicial or "")], capture_output=True, timeout=600,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return None
    elegida = hecho.stdout.decode("utf-8").strip()
    return str(Path(elegida)) if elegida else None


# --- El modo de este ordenador ---

LOCAL, COMPARTIDO = "local", "compartido"


def guardar_ajustes(ajustes: Path = AJUSTES, **valores) -> None:
    """Apunta unos valores en los ajustes de este ordenador, sin tocar lo demás que haya."""
    datos = leer_ajustes(ajustes)
    datos.update({k: str(v) if isinstance(v, Path) else v for k, v in valores.items()})
    ajustes.parent.mkdir(parents=True, exist_ok=True)
    ajustes.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def modo(ajustes: Path = AJUSTES, programa: Path = SECRETOS_PROGRAMA) -> str | None:
    """«local», «compartido» o None si aún no se ha instalado. Un portal de una versión anterior no lo tiene apuntado: si
    tiene `secretos.env` en la carpeta del programa, ya funcionaba con el MySQL; se copia al lado de los ajustes (el
    original se queda) y se apunta «compartido», sin pasar por la instalación."""
    elegido = leer_ajustes(ajustes).get("modo")
    if elegido in (LOCAL, COMPARTIDO):
        return elegido
    if programa.is_file():
        destino = secretos_de(ajustes)
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.exists():
            destino.write_bytes(programa.read_bytes())
        guardar_ajustes(ajustes, modo=COMPARTIDO)
        return COMPARTIDO
    return None


def documentos() -> Path:
    """La carpeta Documentos del usuario, aunque OneDrive la haya movido (se le pregunta a Windows)."""
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

        documentos_id = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
        ruta = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(documentos_id), 0, None, ctypes.byref(ruta)) == 0:
            encontrada = Path(ruta.value)
            ctypes.windll.ole32.CoTaskMemFree(ruta)
            return encontrada
    except (AttributeError, OSError, ValueError):
        pass
    return Path.home() / "Documents"


def datos_local(ajustes: Path = AJUSTES) -> Path:
    """En el modo «solo en este ordenador», dónde están los datos (por defecto, Documentos/Portal ISO 42001)."""
    ruta = leer_ajustes(ajustes).get("datos")
    return Path(ruta) if isinstance(ruta, str) and ruta else documentos() / "Portal ISO 42001"


def comprobar_datos(texto: str) -> Path:
    """La carpeta de los datos locales: no tiene que existir (se crea), pero sí poder crearse y escribir en ella."""
    texto = texto.strip().strip('"').strip()
    if not texto:
        raise CarpetaNoVale("Elige una carpeta con «Examinar» o escribe su ruta.")
    ruta = Path(os.path.expandvars(texto)).expanduser()
    if not ruta.is_absolute():
        raise CarpetaNoVale(f"«{texto}» no es una ruta completa. Tiene que empezar por la unidad, como C:\\…. "
                            "Lo más fácil es usar «Examinar».")
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        prueba = ruta / ".portal-prueba"
        prueba.write_text("", encoding="utf-8")
        prueba.unlink()
    except OSError:
        raise CarpetaNoVale(f"No se puede crear ni guardar nada en «{ruta}». Elige otra carpeta.")
    return ruta


def escribir_secretos(destino: Path, host: str, puerto: int, usuario: str, clave: str, base: str) -> None:
    """El archivo con los datos del MySQL, para que nadie tenga que escribirlo a mano. Fuera del programa y de git."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("# Los datos del MySQL del portal. Los escribe la instalación; no se comparten.\n"
                       f"MYSQL_SERVIDOR={host}\nMYSQL_PUERTO={puerto}\nMYSQL_USUARIO={usuario}\nMYSQL_CLAVE={clave}\n"
                       f"MYSQL_BASE={base}\n", encoding="utf-8")
