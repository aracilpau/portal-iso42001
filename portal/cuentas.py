# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Las cuentas del portal: quién puede entrar y en qué empresas.

Viven en `cuentas.db`, aparte de las empresas: cada empresa tiene su carpeta (`<datos>/<empresa>/`) con su base de
datos y sus pruebas. Las cuentas y las empresas se crean con `scripts/cuentas.py`; el portal solo las lee.

La contraseña nunca se guarda tal cual: se guarda su huella (scrypt, que viene con Python), de la que no se puede sacar
la contraseña. Para comprobarla se calcula la huella de lo escrito y se comparan.

En el portal de verdad, las cuentas y las empresas están en el MySQL: valen desde cualquier ordenador, y cada
cuenta ve solo las empresas que se le asignan. La carpeta de cada empresa sigue en el ordenador, para sus
archivos de pruebas.
"""
import hashlib
import hmac
import secrets
import shutil
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from portal import db

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id      INTEGER PRIMARY KEY,
    correo  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre  TEXT NOT NULL,
    clave   TEXT NOT NULL,
    activo  INTEGER NOT NULL DEFAULT 1,
    creado  TEXT NOT NULL
);

-- `todos`: entran todos los usuarios sin asignarlos (el General)
CREATE TABLE IF NOT EXISTS empresa (
    slug    TEXT PRIMARY KEY,
    nombre  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    todos   INTEGER NOT NULL DEFAULT 0,
    creada  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS miembro (
    usuario_id  INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    empresa     TEXT NOT NULL REFERENCES empresa(slug) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, empresa)
);

-- Quién administra el portal: crea cuentas y empresas y dice quién entra en cada una
CREATE TABLE IF NOT EXISTS administrador (
    usuario_id  INTEGER PRIMARY KEY REFERENCES usuario(id) ON DELETE CASCADE
);
"""

# Las mismas tablas en el MySQL (ver db.ESQUEMA_MYSQL)
ESQUEMA_MYSQL = """
CREATE TABLE IF NOT EXISTS usuario (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    correo  VARCHAR(190) NOT NULL UNIQUE,
    nombre  VARCHAR(190) NOT NULL,
    clave   VARCHAR(255) NOT NULL,
    activo  TINYINT NOT NULL DEFAULT 1,
    creado  VARCHAR(30) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS empresa (
    slug    VARCHAR(190) PRIMARY KEY,
    nombre  VARCHAR(190) NOT NULL UNIQUE,
    todos   TINYINT NOT NULL DEFAULT 0,
    creada  VARCHAR(30) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS miembro (
    usuario_id  INT NOT NULL,
    empresa     VARCHAR(190) NOT NULL,
    PRIMARY KEY (usuario_id, empresa),
    FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (empresa) REFERENCES empresa(slug) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS administrador (
    usuario_id  INT PRIMARY KEY,
    FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

GENERAL = ("general", "General")
# El usuario del portal de prueba (arrancar-prueba.bat): se crea solo, para poder entrar
PRUEBA = ("prueba@ejemplo.com", "Prueba", "prueba")


class ErrorCuentas(Exception):
    """Algo que no se puede hacer, con el porqué en llano."""


@dataclass(frozen=True)
class Usuario:
    id: int
    correo: str
    nombre: str
    activo: bool


@dataclass(frozen=True)
class Empresa:
    slug: str
    nombre: str
    todos: bool


def ruta(datos: Path) -> Path:
    return datos / "cuentas.db"


def bd_de(datos: Path, slug: str) -> Path:
    """La base de datos de una empresa."""
    return datos / slug / "portal.db"


def _conectar(datos: Path) -> sqlite3.Connection:
    """`cuentas.db` en local; el MySQL en el portal de verdad."""
    return db.conectar(ruta(datos))


def _consulta(datos: Path, sql: str, *args) -> list[sqlite3.Row]:
    con = _conectar(datos)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def _cambia(datos: Path, sql: str, *args) -> int:
    con = _conectar(datos)
    try:
        with con:
            return con.execute(sql, args).rowcount
    finally:
        con.close()


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --- La contraseña ---

def huella(clave: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(clave.encode(), salt=sal, n=2 ** 14, r=8, p=1)
    return f"scrypt${sal.hex()}${h.hex()}"


def clave_buena(clave: str, guardada: str) -> bool:
    try:
        _, sal, h = guardada.split("$")
    except ValueError:
        return False
    calculada = hashlib.scrypt(clave.encode(), salt=bytes.fromhex(sal), n=2 ** 14, r=8, p=1)
    return hmac.compare_digest(calculada.hex(), h)


# --- Preparar: la primera vez se crea el General y se pasa ahí lo de antes ---

def iniciar(datos: Path, prueba: bool = False, general: bool = True) -> None:
    """Crea `cuentas.db` si no existe. La primera vez crea el General y le pasa lo que había antes de las
    empresas (`datos/portal.db` y `datos/pruebas/general/`). Borrado el General, no vuelve: ya hay `cuentas.db`.
    Una instalación nueva pide `general=False`: la primera empresa es la que escribe la persona.
    En el portal de prueba crea además un usuario, para poder entrar.
    En el MySQL solo crea las tablas que falten: sin General y sin nada que pasar."""
    datos.mkdir(parents=True, exist_ok=True)
    if db.en_servidor():
        db.preparar_servidor("cuentas", ESQUEMA_MYSQL)
        return
    nueva = not ruta(datos).exists()
    con = _conectar(datos)
    try:
        con.executescript(ESQUEMA)
    finally:
        con.close()
    if not nueva or not general:
        return
    slug, nombre = GENERAL
    _pasar_lo_de_antes(datos, slug)
    _cambia(datos, "INSERT INTO empresa (slug, nombre, todos, creada) VALUES (?, ?, 1, ?)", slug, nombre, _ahora())
    db.iniciar(bd_de(datos, slug))
    if prueba:
        correo, nombre_u, clave = PRUEBA
        crear_usuario(datos, correo, nombre_u, clave)


def _pasar_lo_de_antes(datos: Path, slug: str) -> None:
    viejo, carpeta = datos / "portal.db", datos / slug
    if viejo.exists() and not bd_de(datos, slug).exists():
        carpeta.mkdir(parents=True, exist_ok=True)
        for sufijo in ("", "-journal", "-wal", "-shm"):
            if Path(f"{viejo}{sufijo}").exists():
                Path(f"{viejo}{sufijo}").rename(Path(f"{bd_de(datos, slug)}{sufijo}"))
    pruebas_viejas = datos / "pruebas" / slug
    if pruebas_viejas.is_dir() and not (carpeta / "pruebas").exists():
        carpeta.mkdir(parents=True, exist_ok=True)
        pruebas_viejas.rename(carpeta / "pruebas")
        try:
            (datos / "pruebas").rmdir()  # si se ha quedado vacía
        except OSError:
            pass


# --- Usuarios ---

def _usuario(fila: sqlite3.Row) -> Usuario:
    return Usuario(fila["id"], fila["correo"], fila["nombre"], bool(fila["activo"]))


def _correo_valido(correo: str) -> str:
    correo = correo.strip()
    usuario, arroba, dominio = correo.partition("@")
    if not usuario or not arroba or "." not in dominio or " " in correo:
        raise ErrorCuentas(f"«{correo}» no tiene forma de correo.")
    return correo


def crear_usuario(datos: Path, correo: str, nombre: str, clave: str) -> Usuario:
    correo, nombre = _correo_valido(correo), nombre.strip()
    if not nombre:
        raise ErrorCuentas("Falta el nombre.")
    if not clave:
        raise ErrorCuentas("Falta la contraseña.")
    if usuario(datos, correo):
        raise ErrorCuentas(f"Ya hay una cuenta con el correo {correo}.")
    _cambia(datos, "INSERT INTO usuario (correo, nombre, clave, creado) VALUES (?, ?, ?, ?)",
            correo, nombre, huella(clave), _ahora())
    return usuario(datos, correo)


def usuario(datos: Path, correo: str) -> Usuario | None:
    filas = _consulta(datos, "SELECT * FROM usuario WHERE correo = ?", correo.strip())
    return _usuario(filas[0]) if filas else None


def usuario_por_id(datos: Path, id_: int) -> Usuario | None:
    filas = _consulta(datos, "SELECT * FROM usuario WHERE id = ?", id_)
    return _usuario(filas[0]) if filas else None


def usuarios(datos: Path) -> list[Usuario]:
    return [_usuario(f) for f in _consulta(datos, "SELECT * FROM usuario ORDER BY nombre COLLATE NOCASE")]


def _usuario_o_error(datos: Path, correo: str) -> Usuario:
    u = usuario(datos, correo)
    if u is None:
        raise ErrorCuentas(f"No hay ninguna cuenta con el correo {correo}.")
    return u


def entrar(datos: Path, correo: str, clave: str) -> Usuario | None:
    """El usuario si el correo y la contraseña están bien y la cuenta está activa; si no, None (sin decir qué falla,
    como cualquier página de entrar)."""
    filas = _consulta(datos, "SELECT * FROM usuario WHERE correo = ?", correo.strip())
    if not filas or not filas[0]["activo"] or not clave_buena(clave, filas[0]["clave"]):
        return None
    return _usuario(filas[0])


def cambiar_clave(datos: Path, correo: str, clave: str) -> None:
    u = _usuario_o_error(datos, correo)
    if not clave:
        raise ErrorCuentas("Falta la contraseña.")
    _cambia(datos, "UPDATE usuario SET clave = ? WHERE id = ?", huella(clave), u.id)


def activar(datos: Path, correo: str, activo: bool) -> None:
    """Quitar a alguien no borra lo que hizo: deja de poder entrar y se puede volver a activar. Al último administrador
    no se le puede quitar."""
    u = _usuario_o_error(datos, correo)
    if not activo and u.id in administradores(datos) and not _otro_administrador(datos, u.id):
        raise ErrorCuentas("Es el único administrador: nombra antes a otro.")
    _cambia(datos, "UPDATE usuario SET activo = ? WHERE id = ?", int(activo), u.id)


# --- Empresas ---

def _empresa(fila: sqlite3.Row) -> Empresa:
    return Empresa(fila["slug"], fila["nombre"], bool(fila["todos"]))


def slug_de(nombre: str) -> str:
    """El nombre de la carpeta: sin tildes ni espacios («Ñandú Óptica» → «nandu-optica»)."""
    llano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    return "-".join("".join(c if c.isalnum() else " " for c in llano).split()) or "empresa"


def empresas(datos: Path) -> list[Empresa]:
    return [_empresa(f) for f in _consulta(datos, "SELECT * FROM empresa ORDER BY nombre COLLATE NOCASE")]


def empresa(datos: Path, nombre_o_slug: str) -> Empresa | None:
    # Sin distinguir mayúsculas, también con tilde o ñ («Señal» y «SEÑAL»), que SQLite solo hace con las letras sin tilde
    buscado = nombre_o_slug.strip().casefold()
    return next((e for e in empresas(datos) if buscado in (e.nombre.casefold(), e.slug)), None)


def _empresa_o_error(datos: Path, nombre: str) -> Empresa:
    e = empresa(datos, nombre)
    if e is None:
        raise ErrorCuentas(f"No hay ninguna empresa «{nombre}».")
    return e


def crear_empresa(datos: Path, nombre: str) -> Empresa:
    nombre = nombre.strip()
    if not nombre:
        raise ErrorCuentas("Falta el nombre de la empresa.")
    if empresa(datos, nombre):
        raise ErrorCuentas(f"Ya hay una empresa «{nombre}».")
    base = slug_de(nombre)
    slug, n = base, 2
    while empresa(datos, slug) or (datos / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    db.iniciar(bd_de(datos, slug))
    _cambia(datos, "INSERT INTO empresa (slug, nombre, creada) VALUES (?, ?, ?)", slug, nombre, _ahora())
    return empresa(datos, slug)


def renombrar_empresa(datos: Path, nombre: str, nuevo: str) -> Empresa:
    """Cambia el nombre que se ve; la carpeta se queda como está."""
    e, nuevo = _empresa_o_error(datos, nombre), nuevo.strip()
    if not nuevo:
        raise ErrorCuentas("Falta el nombre nuevo.")
    otra = empresa(datos, nuevo)
    if otra and otra.slug != e.slug:
        raise ErrorCuentas(f"Ya hay una empresa «{nuevo}».")
    _cambia(datos, "UPDATE empresa SET nombre = ? WHERE slug = ?", nuevo, e.slug)
    return empresa(datos, e.slug)


def borrar_empresa(datos: Path, nombre: str, pruebas: Path | None = None) -> None:
    """Para siempre: su base de datos y sus pruebas desaparecen, sin papelera. Si hay un archivo suyo abierto,
    no se borra nada de las cuentas y se avisa. En el MySQL se borra también todo lo suyo de allí. `pruebas`: dónde
    están las carpetas de pruebas si no es en `datos` (en el portal compartido, la carpeta elegida)."""
    e = _empresa_o_error(datos, nombre)
    for carpeta in {datos / e.slug, (pruebas or datos) / e.slug}:
        if carpeta.exists():
            try:
                shutil.rmtree(carpeta)
            except OSError as error:
                raise ErrorCuentas(f"No se ha podido borrar la carpeta de «{e.nombre}»: seguramente hay un archivo "
                                   f"suyo abierto. Ciérralo y vuelve a intentarlo. ({error})")
    db.borrar_espacio(bd_de(datos, e.slug))
    _cambia(datos, "DELETE FROM empresa WHERE slug = ?", e.slug)


def asignar(datos: Path, correo: str, nombre_empresa: str, dentro: bool = True) -> None:
    u, e = _usuario_o_error(datos, correo), _empresa_o_error(datos, nombre_empresa)
    if dentro:
        _cambia(datos, "INSERT OR IGNORE INTO miembro (usuario_id, empresa) VALUES (?, ?)", u.id, e.slug)
    else:
        _cambia(datos, "DELETE FROM miembro WHERE usuario_id = ? AND empresa = ?", u.id, e.slug)


def empresas_de(datos: Path, usuario_id: int) -> list[Empresa]:
    """Las empresas en las que puede entrar alguien: las suyas y las de todos (el General)."""
    return [_empresa(f) for f in _consulta(
        datos, "SELECT * FROM empresa WHERE todos = 1 OR slug IN (SELECT empresa FROM miembro WHERE usuario_id = ?) "
               "ORDER BY nombre COLLATE NOCASE", usuario_id)]


def usuarios_de(datos: Path, slug: str) -> list[Usuario]:
    """Quién puede entrar en una empresa: sus usuarios activos (en una de todos, todos los activos)."""
    e = empresa(datos, slug)
    if e is None:
        return []
    if e.todos:
        return [u for u in usuarios(datos) if u.activo]
    return [_usuario(f) for f in _consulta(
        datos, "SELECT * FROM usuario WHERE activo = 1 AND id IN (SELECT usuario_id FROM miembro WHERE empresa = ?) "
               "ORDER BY nombre COLLATE NOCASE", e.slug)]


def puede_entrar(datos: Path, usuario_id: int, slug: str) -> bool:
    return any(e.slug == slug for e in empresas_de(datos, usuario_id))


# --- Administradores ---

CLAVE_MINIMA = 8


def comprobar_clave(clave: str, repetida: str | None = None) -> None:
    """Una contraseña nueva puesta desde el portal: al menos 8 caracteres y, si se repite, igual."""
    if len(clave) < CLAVE_MINIMA:
        raise ErrorCuentas(f"La contraseña tiene que tener al menos {CLAVE_MINIMA} caracteres.")
    if repetida is not None and clave != repetida:
        raise ErrorCuentas("Las dos contraseñas no coinciden.")


def administradores(datos: Path) -> set[int]:
    """Quién administra. Un portal de una versión anterior no tiene a nadie: lo es la primera cuenta que se creó (activa)."""
    ids = {f["usuario_id"] for f in _consulta(datos, "SELECT usuario_id FROM administrador")}
    if not ids:
        primera = _consulta(datos, "SELECT id FROM usuario WHERE activo = 1 ORDER BY id LIMIT 1")
        if primera:
            _cambia(datos, "INSERT OR IGNORE INTO administrador (usuario_id) VALUES (?)", primera[0]["id"])
            ids = {primera[0]["id"]}
    return ids


def es_administrador(datos: Path, usuario_id: int) -> bool:
    return usuario_id in administradores(datos)


def administrar(datos: Path, correo: str, si: bool = True) -> None:
    """Nombrar o quitar de administrador. Tiene que quedar al menos uno que pueda entrar."""
    u = _usuario_o_error(datos, correo)
    administradores(datos)  # antes que nada: en un portal de antes, que la primera cuenta no pierda serlo
    if si:
        _cambia(datos, "INSERT OR IGNORE INTO administrador (usuario_id) VALUES (?)", u.id)
        return
    if not _otro_administrador(datos, u.id):
        raise ErrorCuentas("Tiene que quedar al menos un administrador: nombra antes a otro.")
    _cambia(datos, "DELETE FROM administrador WHERE usuario_id = ?", u.id)


def _otro_administrador(datos: Path, usuario_id: int) -> bool:
    activos = {u.id for u in usuarios(datos) if u.activo}
    return bool((administradores(datos) & activos) - {usuario_id})


def cambiar_la_propia(datos: Path, usuario_id: int, actual: str, nueva: str, repetida: str) -> None:
    """Cada uno cambia la suya, escribiendo antes la actual."""
    u = usuario_por_id(datos, usuario_id)
    if u is None or entrar(datos, u.correo, actual) is None:
        raise ErrorCuentas("La contraseña actual no es correcta.")
    comprobar_clave(nueva, repetida)
    cambiar_clave(datos, u.correo, nueva)


def poner_empresas(datos: Path, correo: str, slugs: set[str]) -> None:
    """En qué empresas entra alguien: las marcadas, y en ninguna más (las de todos, como el General, no cuentan)."""
    u = _usuario_o_error(datos, correo)
    for e in empresas(datos):
        if not e.todos:
            asignar(datos, u.correo, e.slug, e.slug in slugs)
