# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La instalación: lo que se ve la primera vez que se arranca el portal.

Se elige el modo: «solo en este ordenador» (los datos en una carpeta, sin instalar nada más) o «compartido con mi
equipo» (los datos en un MySQL y los archivos en una carpeta compartida). Después, la primera cuenta y la primera
empresa; o, si el MySQL ya tiene cuentas, nada: es un compañero que se une a un equipo que ya existe.

Aquí está lo que no es pantalla: probar la conexión con el MySQL, mirar si ya tiene cuentas y crear la primera. Las
pantallas están en main.py y en templates/instalar*.html.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pymysql

from portal import config, cuentas, db
from portal import servidor as srv

# Lo que dice el MySQL cuando algo falla, en llano (los números son los de sus errores)
MOTIVOS = {
    1045: "El usuario o la contraseña no son correctos.",
    1044: "Ese usuario no tiene permiso para usar esa base de datos.",
    1049: "No existe la base de datos «{base}» en ese servidor. Créala antes (el manual lo explica) o revisa el nombre.",
    2003: "No se encuentra el servidor en «{host}», puerto {puerto}. Revisa la dirección y el puerto, y que tienes "
          "internet.",
    2005: "No se encuentra el servidor «{host}». Revisa la dirección.",
}
NO_CONECTA = "No se ha podido conectar con el MySQL. Pásale este mensaje a quien lo montó: {error}"
CLAVE_MINIMA = 8


class ErrorInstalar(Exception):
    """Algo de lo escrito no vale; el mensaje dice qué, en llano."""


def servidor_de(host: str, puerto: str, usuario: str, clave: str, base: str) -> srv.Servidor:
    """Los datos del formulario, comprobados: que no falte nada y que el puerto sea un número."""
    host, usuario, base = host.strip(), usuario.strip(), base.strip()
    faltan = [n for n, v in (("la dirección", host), ("el usuario", usuario), ("la contraseña", clave),
                             ("la base de datos", base)) if not v]
    if faltan:
        raise ErrorInstalar(f"Falta {', '.join(faltan)}.")
    try:
        numero = int(puerto.strip() or 3306)
    except ValueError:
        raise ErrorInstalar(f"El puerto tiene que ser un número (normalmente, 3306), no «{puerto}».")
    return srv.Servidor(host, numero, usuario, clave, base)


def probar_conexion(s: srv.Servidor) -> str | None:
    """None si se puede conectar; si no, por qué, en llano."""
    try:
        con = pymysql.connect(host=s.host, port=s.puerto, user=s.usuario, password=s.clave, database=s.base,
                              connect_timeout=8)
    except pymysql.err.MySQLError as error:
        codigo = error.args[0] if error.args and isinstance(error.args[0], int) else None
        if codigo in MOTIVOS:
            return MOTIVOS[codigo].format(host=s.host, puerto=s.puerto, base=s.base)
        return NO_CONECTA.format(error=error.args[-1] if error.args else error)
    con.close()
    return None


@dataclass
class Instalador:
    """Dónde apunta la instalación lo elegido y cómo habla con el MySQL. Las pruebas automáticas cambian `probar` y
    `usar` para no tocar ningún MySQL: con `usar` devolviendo None, «el MySQL» es SQLite en `datos_compartido`."""
    ajustes: Path = config.AJUSTES
    probar: Callable[[srv.Servidor], str | None] = probar_conexion
    usar: Callable[[srv.Servidor], srv.Servidor | None] = field(default=lambda s: s)
    datos_compartido: Path = config.DATOS_SERVIDOR
    programa: Path = config.SECRETOS_PROGRAMA  # dónde estaba secretos.env en versiones anteriores (las pruebas, en otra carpeta)

    @property
    def secretos(self) -> Path:
        return config.secretos_de(self.ajustes)

    def modo(self) -> str | None:
        return config.modo(self.ajustes, self.programa)

    def servidor(self) -> srv.Servidor | None:
        """El MySQL apuntado en este ordenador, listo para usar."""
        return self.usar(srv.leer(self.secretos))


def hay_cuentas(datos: Path) -> bool:
    """Si el portal (en el MySQL, el que esté en uso) ya tiene cuentas: entonces es de un equipo que ya existe."""
    cuentas.iniciar(datos, general=False)
    return bool(cuentas.usuarios(datos))


def crear_primera(datos: Path, nombre: str, correo: str, clave: str, repetida: str,
                  empresa: str) -> tuple[cuentas.Usuario, cuentas.Empresa]:
    """La primera cuenta y la primera empresa, con la cuenta dentro. Si algo no vale, no crea nada."""
    if not empresa.strip():
        raise ErrorInstalar("Falta el nombre de la empresa.")
    if not nombre.strip():
        raise ErrorInstalar("Falta tu nombre.")
    if len(clave) < CLAVE_MINIMA:
        raise ErrorInstalar(f"La contraseña tiene que tener al menos {CLAVE_MINIMA} caracteres.")
    if clave != repetida:
        raise ErrorInstalar("Las dos contraseñas no coinciden.")
    cuentas.iniciar(datos, general=False)
    if cuentas.usuarios(datos):
        raise ErrorInstalar("Este portal ya tiene cuentas: entra con la tuya.")
    try:
        u = cuentas.crear_usuario(datos, correo.strip(), nombre.strip(), clave)
        # Si ya había una empresa con ese nombre (un MySQL con empresas pero sin cuentas), se usa esa
        e = cuentas.empresa(datos, empresa) or cuentas.crear_empresa(datos, empresa)
    except cuentas.ErrorCuentas as error:
        raise ErrorInstalar(str(error))
    cuentas.asignar(datos, u.correo, e.nombre)
    cuentas.administrar(datos, u.correo)  # la primera cuenta administra el portal
    db.iniciar(cuentas.bd_de(datos, e.slug))
    return u, e
