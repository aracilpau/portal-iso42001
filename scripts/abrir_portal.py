# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Lo que se abre al pulsar la notificación de los avisos (el enlace portal-iso://).

Si el portal está apagado, lo enciende (el de verdad, con el MySQL) en una ventana minimizada (se apaga cerrándola o con parar.bat, como siempre) y
abre Inicio en el navegador. No usa nada de lo que trae el enlace: siempre abre Inicio.
"""
import os
import socket
import subprocess
import time
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUERTO = 8000


def encendido() -> bool:
    try:
        socket.create_connection(("127.0.0.1", PUERTO), timeout=0.5).close()
        return True
    except OSError:
        return False


if __name__ == "__main__":
    if not encendido():
        python = RAIZ / ".venv" / "Scripts" / "python.exe"
        subprocess.Popen(["cmd", "/c", "start", "Portal ISO 42001", "/min", str(python), "-m", "uvicorn",
                          "portal.main:app", "--port", str(PUERTO)], cwd=RAIZ,
                         env={**os.environ, "PORTAL_SERVIDOR": "1"})
        limite = time.monotonic() + 30
        while not encendido() and time.monotonic() < limite:
            time.sleep(0.5)
    webbrowser.open(f"http://localhost:{PUERTO}/")
