# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Lo común a todas las pruebas."""
from contextlib import contextmanager

import pytest

from portal import avisos


class EnvioDeMentira(avisos.Envio):
    """Los avisos por correo sin Outlook, sin notificaciones y sin mirar las tareas de Windows: apunta lo que se
    habría mandado. `falla` hace que el correo no salga."""

    def __init__(self, cuentas: list[str] | None = None, programada: bool = True, falla: str = ""):
        self.correos, self.notificaciones = [], []

        def correo(para, asunto, html, cuenta):
            if falla:
                raise avisos.AvisoFallido(falla)
            self.correos.append({"para": para, "asunto": asunto, "html": html, "cuenta": cuenta})

        super().__init__(correo=correo, notificacion=lambda t, m: self.notificaciones.append((t, m)),
                         cuentas=lambda: list(cuentas or []), programada=lambda: programada)


@pytest.fixture(autouse=True)
def sin_claude_de_verdad(monkeypatch):
    """Ninguna prueba llama al Claude de verdad, aunque esté en el ordenador: por defecto no está. Las que lo necesitan
    ponen uno de mentira encima («Hacer borrador» lo llama)."""
    from portal import ia

    async def no_esta(*args, **kwargs):
        raise ia.ClaudeNoDisponible("Claude no está disponible: no se encuentra Claude Code en este ordenador.")
    monkeypatch.setattr(ia, "disponible", lambda: False)
    monkeypatch.setattr(ia, "tarea", no_esta)


@pytest.fixture(autouse=True)
def sin_correo_de_verdad(monkeypatch):
    """Ninguna prueba manda correos ni toca Windows de verdad, aunque cree el portal sin decir cómo se envía."""
    monkeypatch.setattr(avisos, "Envio", EnvioDeMentira)


@pytest.fixture(autouse=True)
def sin_mysql():
    """Todas las pruebas, en local (SQLite): ninguna toca el MySQL, aunque otra lo haya puesto."""
    from portal import db
    db.usar_servidor(None)
    yield
    db.usar_servidor(None)


# --- Entrar en el portal: sin correo y contraseña no se ve nada ---

USUARIO = ("ana@ejemplo.com", "Ana", "clave-de-ana")


def entrar(cliente, empresa="general", usuario=USUARIO):
    """Entra con el usuario de las pruebas y elige la empresa."""
    from portal import main
    r = cliente.post("/entrar", data={"correo": usuario[0], "clave": usuario[2]})
    assert r.status_code == 200 and "/entrar" not in str(r.url), "no ha podido entrar"
    if empresa:
        cliente.post(f"/empresas/{empresa}")
    return cliente


def preparar_cuentas(datos):
    """Las cuentas de las pruebas: el General y el usuario de las pruebas."""
    from portal import cuentas
    cuentas.iniciar(datos)
    if cuentas.usuario(datos, USUARIO[0]) is None:
        cuentas.crear_usuario(datos, *USUARIO)
    return datos


@contextmanager
def en_portal(bd, empresa="general", **opciones):
    """El portal de las pruebas, ya dentro de una empresa. `bd` es la base de datos del General
    (`<datos>/general/portal.db`): la carpeta de datos es la de encima."""
    from fastapi.testclient import TestClient
    from portal.main import crear_app
    datos = preparar_cuentas(bd.parent.parent)
    with TestClient(crear_app(datos, **opciones)) as c:
        entrar(c, empresa)
        yield c
