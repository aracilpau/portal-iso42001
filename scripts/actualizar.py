# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Pone el portal al día con la última versión publicada en GitHub. Lo lanza `actualizar.bat`.

1. Lee la versión publicada (el fichero VERSION del repositorio) y la compara con la de esta carpeta. Si es la misma,
   dice «Ya estás al día» y no hace nada más.
2. Si hay una más nueva, pregunta. Con un sí, descarga la versión entera (el ZIP de GitHub) y comprueba que está bien.
3. Apaga el portal, guarda el programa de ahora en «versión anterior» (en la carpeta de los ajustes, AppData) y pone el
   nuevo. Si algo falla a mitad, devuelve el de antes tal como estaba.

No toca los datos, los ajustes ni las contraseñas: no están en la carpeta del programa (y lo que sí puede estar en
ella, `datos/`, `secretos.env` o el entorno de Python, se queda donde está). Solo se conecta a GitHub para leer y
descargar; no envía nada.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PROGRAMA = Path(__file__).resolve().parent.parent
REPOSITORIO = "aracilpau/portal-iso42001"
URL_VERSION = f"https://raw.githubusercontent.com/{REPOSITORIO}/main/VERSION"
URL_ZIP = f"https://github.com/{REPOSITORIO}/archive/refs/heads/main.zip"
AJUSTES = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Portal ISO 42001"
# Lo que hay en la carpeta del programa y no es del programa: no se mueve ni se cambia
SE_QUEDA = {".venv", "datos", "datos-prueba", "datos-servidor", "secretos.env", ".git"}
# Lo mínimo que tiene que traer una versión para darla por buena
IMPRESCINDIBLE = ("VERSION", "arrancar.bat", "requirements.txt", "portal/main.py")


class NoSeActualiza(Exception):
    """Algo impide actualizar; el texto dice qué, en llano. No se ha cambiado nada."""


def leer_version(carpeta: Path) -> str:
    """La versión de una carpeta del programa («2026-11-17 10:32»), o "" si no la sabe (las de antes no la traían)."""
    f = carpeta / "VERSION"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else ""


def legible(version: str) -> str:
    """«2026-11-17 10:32» → «17/11/2026»."""
    if len(version) >= 10 and version[4] == "-" and version[7] == "-":
        return f"{version[8:10]}/{version[5:7]}/{version[:4]}"
    return version or "sin fecha (anterior a las actualizaciones automáticas)"


def _bajar(url: str, tope: int = 60) -> bytes:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "portal-iso42001"}),
                                    timeout=tope) as r:
            return r.read()
    except OSError as e:  # sin internet, GitHub caído, un proxy…
        raise NoSeActualiza(f"No se ha podido conectar con GitHub ({e}). Comprueba que tienes internet y vuelve a "
                            "probar.") from None


def version_publicada() -> str:
    return _bajar(URL_VERSION, tope=20).decode("utf-8").strip()


def descargar(destino: Path) -> Path:
    """Descarga el ZIP de la versión publicada y lo descomprime en `destino`. Devuelve la carpeta del programa nuevo."""
    datos = _bajar(URL_ZIP, tope=300)
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            z.extractall(destino)  # extractall no deja salir nada de `destino` (quita «..» y rutas absolutas)
    except zipfile.BadZipFile:
        raise NoSeActualiza("La descarga ha llegado incompleta. Vuelve a probar.") from None
    carpetas = [c for c in destino.iterdir() if c.is_dir()]
    return carpetas[0] if len(carpetas) == 1 else destino  # GitHub lo mete todo en «portal-iso42001-main/»


def comprobar(nueva: Path) -> None:
    falta = [f for f in IMPRESCINDIBLE if not (nueva / f).is_file()]
    if falta:
        raise NoSeActualiza(f"La versión descargada no está completa (falta {', '.join(falta)}). No se ha cambiado nada.")
    # El ZIP de GitHub trae los .bat con los finales de línea de Linux, y Windows a veces los lee mal: se ponen los suyos
    for bat in nueva.glob("*.bat"):
        texto = bat.read_bytes().replace(b"\r\n", b"\n")
        bat.write_bytes(texto.replace(b"\n", b"\r\n"))


def apagar(puerto: str) -> None:
    """Apaga el portal de este puerto, si está encendido (lo mismo que parar.bat)."""
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
    for linea in r.stdout.splitlines():
        partes = linea.split()
        # El que escucha en el puerto («LISTENING», o «ESCUCHANDO» en algunos Windows en español)
        if len(partes) >= 5 and partes[0] == "TCP" and partes[1].endswith(f":{puerto}") \
                and partes[2] in ("0.0.0.0:0", "[::]:0"):
            subprocess.run(["taskkill", "/PID", partes[4], "/T", "/F"], capture_output=True)


def cambiar(programa: Path, nueva: Path, anterior: Path) -> None:
    """Guarda el programa de ahora en `anterior` y pone el nuevo. Si algo falla, lo deja como estaba."""
    if anterior.exists():
        shutil.rmtree(anterior)  # solo se guarda la última
    anterior.mkdir(parents=True)
    movidos: list[str] = []
    puestos: list[str] = []
    try:
        for hijo in sorted(programa.iterdir()):
            if hijo.name not in SE_QUEDA:
                shutil.move(str(hijo), str(anterior / hijo.name))
                movidos.append(hijo.name)
        for hijo in sorted(nueva.iterdir()):
            if hijo.name in SE_QUEDA:
                continue
            puestos.append(hijo.name)
            if hijo.is_dir():
                shutil.copytree(hijo, programa / hijo.name)
            else:
                shutil.copy2(hijo, programa / hijo.name)
    except Exception as e:
        for nombre in puestos:  # fuera lo nuevo, a medias o no
            p = programa / nombre
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()
        for nombre in movidos:  # y vuelve lo de antes
            shutil.move(str(anterior / nombre), str(programa / nombre))
        raise NoSeActualiza(f"Ha fallado al cambiar los archivos ({e}). Se ha dejado la versión de antes, tal como "
                            "estaba.") from None


def actualizar(programa: Path = PROGRAMA, anterior: Path = AJUSTES / "version-anterior",
               publicada=version_publicada, bajar=descargar, preguntar=input, apagar=apagar,
               puerto: str = "8000", decir=print) -> bool:
    """Todo el recorrido. Devuelve si ha cambiado el programa."""
    actual, nueva = leer_version(programa), publicada()
    if not nueva:
        raise NoSeActualiza("GitHub no dice qué versión hay publicada. Vuelve a probar más tarde.")
    if actual and actual >= nueva:
        decir(f"Ya estás al día: tienes la versión del {legible(actual)}, la última publicada.")
        return False
    decir(f"Hay una versión nueva: la del {legible(nueva)}. Tienes la del {legible(actual)}.")
    decir("Se cambia el programa; tus datos, tus ajustes y las contraseñas no se tocan.")
    if preguntar("¿Actualizar ahora? Escribe s y pulsa Intro (cualquier otra cosa, no): ").strip().lower() not in ("s", "si", "sí"):
        decir("No se ha cambiado nada.")
        return False
    with tempfile.TemporaryDirectory() as temporal:
        decir("Descargando…")
        carpeta = bajar(Path(temporal))
        comprobar(carpeta)
        decir("Apagando el portal…")
        apagar(puerto)
        decir("Cambiando los archivos…")
        cambiar(programa, carpeta, anterior)
    decir(f"Hecho: ya tienes la versión del {legible(leer_version(programa))}.")
    decir(f"La versión de antes queda guardada en {anterior}, por si hiciera falta volver a ella.")
    return True


def main() -> int:
    try:
        cambiado = actualizar(puerto=os.environ.get("PORTAL_PUERTO") or "8000")
    except NoSeActualiza as e:
        print(f"\nNo se ha actualizado. {e}")
        return 1
    return 0 if cambiado else 2  # 2: no hay que arrancar nada nuevo


if __name__ == "__main__":
    sys.exit(main())
