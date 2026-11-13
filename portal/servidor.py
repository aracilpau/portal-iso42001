# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El MySQL del portal de verdad.

El portal de verdad guarda todo en el MySQL: las cuentas, las empresas y lo que rellena cada una. El portal local, el
de prueba y las pruebas automáticas siguen con SQLite. Para no escribir cada consulta dos veces, `db.py` y
`cuentas.py` las escriben como siempre (en el dialecto de SQLite) y aquí se traducen al del MySQL: son casi iguales,
con unas pocas palabras distintas («si ya existe, no hagas nada», «si ya existe, actualízalo»…).

La clave del MySQL está en `secretos.env`, que no va en git (regla 3 de datos) y se pasa en mano. Sin él, o
sin internet, el portal lo dice.

Conectar al MySQL tarda casi medio segundo y cada consulta unos 50 ms (está en AWS, en Irlanda): cada hilo del portal
guarda su conexión abierta y la reutiliza.
"""
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import pymysql
import pymysql.cursors

# Lo que se ve si falta algo: el texto es para la persona
FALTA_SECRETOS = ("Falta el archivo secretos.env, con los datos del MySQL. Pídeselos a quien administre el portal: "
                  "el manual explica dónde va.")
SIN_CONEXION = "Sin conexión con el servidor. Comprueba que tienes internet y vuelve a intentarlo."

# Los errores de pymysql que quieren decir «se ha perdido la conexión»: se reintenta una vez con una nueva
PERDIDA = {2006, 2013, 2055}
# Dos que guardan lo mismo a la vez y el MySQL para a uno («deadlock», o espera demasiado): una orden suelta se repite
OCUPADO = {1205, 1213}
SERVIDOR_OCUPADO = "El servidor estaba ocupado con otro cambio a la vez y no se ha guardado. Vuelve a intentarlo."


class SinConexion(Exception):
    """No se puede hablar con el MySQL: falta secretos.env, no hay internet o la clave no vale."""


@dataclass(frozen=True)
class Servidor:
    host: str = ""
    puerto: int = 3306
    usuario: str = ""
    clave: str = ""
    base: str = "iso42001"
    problema: str = ""   # si no se puede usar, por qué (falta secretos.env…)


def leer(secretos: Path) -> Servidor:
    """Los datos de conexión de `secretos.env` (líneas CLAVE=valor). Nunca falla: si falta algo, lo dice en
    `problema` y la primera consulta avisa."""
    if not secretos.exists():
        return Servidor(problema=FALTA_SECRETOS)
    valores = {}
    for linea in secretos.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            k, v = linea.split("=", 1)
            valores[k.strip()] = v.strip()
    if not all(valores.get(k) for k in ("MYSQL_SERVIDOR", "MYSQL_USUARIO", "MYSQL_CLAVE")):
        return Servidor(problema=f"El archivo secretos.env está incompleto. {FALTA_SECRETOS.split('. ', 1)[1]}")
    return Servidor(valores["MYSQL_SERVIDOR"], int(valores.get("MYSQL_PUERTO") or 3306), valores["MYSQL_USUARIO"],
                    valores["MYSQL_CLAVE"], valores.get("MYSQL_BASE") or "iso42001")


# --- El traductor ---

def traducir(sql: str, con_valores: bool) -> str:
    """Una consulta escrita para SQLite, en el dialecto del MySQL."""
    if con_valores:
        sql = sql.replace("%", "%%")  # pymysql usa % para meter los valores
    sql = re.sub(r"\bINSERT OR IGNORE\b", "INSERT IGNORE", sql)
    sql = re.sub(r"\bINSERT OR REPLACE\b", "REPLACE", sql)
    sql = re.sub(r"\bON CONFLICT\s*\([^)]*\)\s*DO UPDATE SET\b", "ON DUPLICATE KEY UPDATE", sql)
    sql = re.sub(r"\bexcluded\.(\w+)", r"VALUES(\1)", sql)
    sql = re.sub(r"\s+COLLATE NOCASE\b", "", sql)  # en el MySQL las columnas ya ignoran mayúsculas
    return sql.replace("?", "%s")


# --- La conexión ---

class Conexion:
    """Se usa como una conexión de SQLite: `execute`, `with con:` para guardar de una vez y `close`. Las filas son
    diccionarios (`fila["nombre"]`), como las de SQLite."""

    def __init__(self, servidor: Servidor, cache: threading.local):
        self._servidor, self._cache, self._dentro = servidor, cache, False

    def _abrir(self) -> pymysql.connections.Connection:
        con = getattr(self._cache, "con", None)
        if con is None:
            s = self._servidor
            try:
                con = pymysql.connect(host=s.host, port=s.puerto, user=s.usuario, password=s.clave, database=s.base,
                                      charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=True,
                                      connect_timeout=10, read_timeout=30, write_timeout=30)
            except pymysql.err.MySQLError as error:
                raise SinConexion(SIN_CONEXION) from error
            with con.cursor() as c:  # que avise si algo no cabe, en vez de cortarlo callado
                c.execute("SET SESSION sql_mode = 'STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION'")
            self._cache.con = con
        return con

    def _olvidar(self) -> None:
        con, self._cache.con = getattr(self._cache, "con", None), None
        if con is not None:
            try:
                con.close()
            except pymysql.err.MySQLError:
                pass

    def execute(self, sql: str, valores=()):
        valores = tuple(valores) if valores else None
        consulta = traducir(sql, valores is not None)
        for intento in (1, 2, 3):
            con = self._abrir()
            try:
                cur = con.cursor()
                cur.execute(consulta, valores)
                return cur
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as error:
                codigo = error.args[0] if error.args else None
                if codigo in OCUPADO:
                    if self._dentro:
                        raise SinConexion(SERVIDOR_OCUPADO) from error
                    if intento < 3:  # una orden suelta: el MySQL ya la ha deshecho, se repite
                        continue
                    raise SinConexion(SERVIDOR_OCUPADO) from error
                self._olvidar()
                # Fuera de un «guardar de una vez», una conexión que se cortó se reabre y se repite la consulta
                if intento == 1 and not self._dentro and (codigo in PERDIDA or isinstance(error, pymysql.err.InterfaceError)):
                    continue
                raise SinConexion(SIN_CONEXION) from error

    def __enter__(self):
        for intento in (1, 2):
            try:
                self._abrir().begin()
                break
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as error:
                self._olvidar()  # la conexión guardada se había cortado: se abre otra
                if intento == 2:
                    raise SinConexion(SIN_CONEXION) from error
        self._dentro = True
        return self

    def __exit__(self, tipo, error, traza):
        self._dentro = False
        con = getattr(self._cache, "con", None)
        if con is None:
            return False
        try:
            if tipo is None:
                con.commit()
            else:
                con.rollback()
        except pymysql.err.MySQLError as fallo:
            self._olvidar()
            if tipo is None:
                raise SinConexion(SIN_CONEXION) from fallo
        return False

    def commit(self) -> None:
        """Fuera de un «guardar de una vez», cada orden ya queda guardada al momento."""

    def close(self) -> None:
        """La conexión se queda abierta para la siguiente consulta de este hilo."""


_caches: dict[Servidor, threading.local] = {}
_preparado: set[tuple[Servidor, str]] = set()
_cerrojo = threading.Lock()


def conectar(servidor: Servidor) -> Conexion:
    if servidor.problema:
        raise SinConexion(servidor.problema)
    with _cerrojo:
        cache = _caches.setdefault(servidor, threading.local())
    return Conexion(servidor, cache)


def preparar(servidor: Servidor, nombre: str, esquema: str) -> None:
    """Crea las tablas que falten, una vez por arranque. `esquema`: varias órdenes separadas por «;»."""
    if (servidor, nombre) in _preparado:
        return
    con = conectar(servidor)
    for orden in esquema.split(";"):
        if orden.strip():
            con.execute(orden)
    _preparado.add((servidor, nombre))
