# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La base de datos del portal (SQLite; el portal de verdad, en el MySQL).

Solo guarda lo que rellena cada espacio. La guía (requisitos, puntos, ayudas) no está aquí: vive en
guia/datos.py y es la misma para todos los espacios.

En local, cada empresa tiene su archivo `portal.db` con un solo espacio, «general». En el MySQL están todas juntas: cada
empresa es un espacio, con el nombre de su carpeta. Las consultas se escriben para SQLite y `servidor.py` las traduce.
"""
import contextvars
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import pymysql

from portal import servidor as srv

ESQUEMA = """
CREATE TABLE IF NOT EXISTS espacio (
    id      INTEGER PRIMARY KEY,
    slug    TEXT NOT NULL UNIQUE,
    nombre  TEXT NOT NULL,
    creado  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Puntos marcados a mano. Los que se cumplen solos (apoyados) no se guardan: se calculan,
-- así nunca se descuadran con los requisitos en los que se apoyan.
-- marcado_en: el día en que se cumplió o se renovó por última vez.
-- vence_manual: la fecha de vencimiento si se recolocó a mano en ajustes.
CREATE TABLE IF NOT EXISTS punto_marcado (
    espacio_id    INTEGER NOT NULL REFERENCES espacio(id),
    punto         TEXT NOT NULL,
    marcado_en    TEXT NOT NULL DEFAULT (datetime('now')),
    vence_manual  TEXT,
    marcado_por   TEXT NOT NULL DEFAULT '',  -- quién lo marcó o renovó; '' antes de los usuarios
    PRIMARY KEY (espacio_id, punto)
);

-- Ajustes sueltos de cada espacio (hoy, la antelación de «Vence pronto»)
CREATE TABLE IF NOT EXISTS ajuste (
    espacio_id  INTEGER NOT NULL REFERENCES espacio(id),
    clave       TEXT NOT NULL,
    valor       TEXT NOT NULL,
    PRIMARY KEY (espacio_id, clave)
);

-- La Declaración de Aplicabilidad: un control sin fila está sin decidir
CREATE TABLE IF NOT EXISTS aplicabilidad (
    espacio_id   INTEGER NOT NULL REFERENCES espacio(id),
    control      TEXT NOT NULL,
    aplica       INTEGER NOT NULL,   -- 1 aplica, 0 no aplica
    porque       TEXT NOT NULL,
    decidido_en  TEXT NOT NULL,
    PRIMARY KEY (espacio_id, control)
);

-- Cada decisión y cada cambio de la Declaración, con su motivo
CREATE TABLE IF NOT EXISTS cambio_aplicabilidad (
    id          INTEGER PRIMARY KEY,
    espacio_id  INTEGER NOT NULL REFERENCES espacio(id),
    control     TEXT NOT NULL,
    fecha       TEXT NOT NULL,
    antes       TEXT NOT NULL,       -- «sin decidir», «aplica» o «no aplica»
    ahora       TEXT NOT NULL,
    motivo      TEXT NOT NULL,
    quien       TEXT NOT NULL DEFAULT ''
);

-- El inventario de IA: una ficha por sistema. No se borran, se retiran.
CREATE TABLE IF NOT EXISTS sistema (
    id               INTEGER PRIMARY KEY,
    espacio_id       INTEGER NOT NULL REFERENCES espacio(id),
    nombre           TEXT NOT NULL,
    tipo             TEXT NOT NULL,              -- «producto» o «herramienta»
    para_que         TEXT NOT NULL DEFAULT '',   -- A.4.2
    datos            TEXT NOT NULL DEFAULT '',   -- A.4.3
    herramientas     TEXT NOT NULL DEFAULT '',   -- A.4.4
    infraestructura  TEXT NOT NULL DEFAULT '',   -- A.4.5
    personas         TEXT NOT NULL DEFAULT '',   -- A.4.6
    actualizado_en   TEXT NOT NULL,
    retirado_en      TEXT,
    UNIQUE (espacio_id, nombre COLLATE NOCASE)
);

-- Las marcas de cada línea de un punto por sistema: como punto_marcado, pero por sistema
CREATE TABLE IF NOT EXISTS punto_sistema (
    espacio_id    INTEGER NOT NULL REFERENCES espacio(id),
    punto         TEXT NOT NULL,
    sistema_id    INTEGER NOT NULL REFERENCES sistema(id),
    marcado_en    TEXT NOT NULL,
    vence_manual  TEXT,
    marcado_por   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (espacio_id, punto, sistema_id)
);

-- Recordatorios intermedios por requisito
CREATE TABLE IF NOT EXISTS recordatorio (
    espacio_id      INTEGER NOT NULL REFERENCES espacio(id),
    requisito       TEXT NOT NULL,
    meses           INTEGER NOT NULL,   -- 0: sin recordatorio, aunque tenga uno por defecto
    desde           TEXT NOT NULL,      -- cuándo se configuró
    hecho_en        TEXT,               -- el último «Hecho»
    proximo_manual  TEXT,               -- ya no se usa: se quitó recolocarlo a mano
    PRIMARY KEY (espacio_id, requisito)
);

-- Plazos cambiados en ajustes. Sin fila, el requisito usa el plazo por defecto;
-- con meses NULL, no vence por fecha.
CREATE TABLE IF NOT EXISTS plazo (
    espacio_id  INTEGER NOT NULL REFERENCES espacio(id),
    requisito   TEXT NOT NULL,
    meses       INTEGER,
    PRIMARY KEY (espacio_id, requisito)
);

-- Lo que se ha hecho en el portal, para la página «Actividad». Solo se apunta: no se usa
-- para ninguna cuenta.
CREATE TABLE IF NOT EXISTS actividad (
    id          INTEGER PRIMARY KEY,
    espacio_id  INTEGER NOT NULL REFERENCES espacio(id),
    cuando      TEXT NOT NULL,      -- fecha y hora, aaaa-mm-ddThh:mm:ss
    accion      TEXT NOT NULL,      -- p. ej. «marcado», «subido», «sistema_alta» (ver ACCIONES)
    requisito   TEXT,
    punto       TEXT,
    sistema     TEXT,               -- el nombre del sistema en ese momento
    detalle     TEXT NOT NULL DEFAULT '',
    quien       TEXT NOT NULL DEFAULT ''   -- el nombre de quien lo hizo; «el portal» si lo hizo solo
);

-- La nota «cómo lo hacemos aquí» de cada requisito
CREATE TABLE IF NOT EXISTS nota (
    espacio_id   INTEGER NOT NULL REFERENCES espacio(id),
    requisito    TEXT NOT NULL,
    texto        TEXT NOT NULL,
    actualizada  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (espacio_id, requisito)
);

-- Las propuestas de la IA para la Declaración: una por control, hasta que se acepta o se descarta.
-- En FALTA SABER, «porque» es la pregunta y «contestado», lo que respondió la persona.
-- «quien» dice si la decidió el portal con el cuestionario o la IA; «aviso», si algo no cuadra.
CREATE TABLE IF NOT EXISTS propuesta (
    espacio_id   INTEGER NOT NULL REFERENCES espacio(id),
    control      TEXT NOT NULL,
    decision     TEXT NOT NULL CHECK (decision IN ('aplica', 'no_aplica', 'falta')),
    porque       TEXT NOT NULL,
    apoyo        TEXT NOT NULL DEFAULT '',
    contestado   TEXT NOT NULL DEFAULT '',
    quien        TEXT NOT NULL DEFAULT 'ia' CHECK (quien IN ('portal', 'ia')),
    aviso        TEXT NOT NULL DEFAULT '',
    creada       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (espacio_id, control)
);

-- Las revisiones de la IA de los archivos de un punto: la última de cada punto o línea de sistema
-- (sistema_id 0 si el punto no va por sistema). La huella dice con qué archivos se hizo, para saber si es antigua.
-- El último borrador hecho con IA de cada documento: si lo que se le da a Claude no cambia (la huella),
-- se devuelve este sin volver a llamarle
CREATE TABLE IF NOT EXISTS borrador_ia (
    espacio_id  INTEGER NOT NULL REFERENCES espacio(id),
    documento   TEXT NOT NULL,       -- el nombre de la plantilla o, en la genérica, el código del requisito
    huella      TEXT NOT NULL,
    texto       TEXT NOT NULL,
    creado      TEXT NOT NULL,
    PRIMARY KEY (espacio_id, documento)
);

-- Lo que la IA dice que le falta saber al hacer un borrador; se contesta en «Empresa»
CREATE TABLE IF NOT EXISTS pregunta_ia (
    id          INTEGER PRIMARY KEY,
    espacio_id  INTEGER NOT NULL REFERENCES espacio(id),
    documento   TEXT NOT NULL,       -- de qué borrador viene
    texto       TEXT NOT NULL,
    respuesta   TEXT NOT NULL DEFAULT '',
    creada      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revision (
    espacio_id   INTEGER NOT NULL REFERENCES espacio(id),
    punto        TEXT NOT NULL,
    sistema_id   INTEGER NOT NULL DEFAULT 0,
    veredicto    TEXT NOT NULL CHECK (veredicto IN ('si', 'no', 'nose')),
    porque       TEXT NOT NULL,
    apoyo        TEXT NOT NULL DEFAULT '',
    falta        TEXT NOT NULL DEFAULT '',
    huella       TEXT NOT NULL,
    creada       TEXT NOT NULL,
    PRIMARY KEY (espacio_id, punto, sistema_id)
);
"""

# Las mismas tablas en el MySQL (5.7): los textos que forman parte de una clave van en VARCHAR (190 letras caben en
# un índice) y sin valores por defecto calculados (los pone el portal). Sin comentarios: se separan por «;».
ESQUEMA_MYSQL = """
CREATE TABLE IF NOT EXISTS espacio (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    slug    VARCHAR(190) NOT NULL UNIQUE,
    nombre  VARCHAR(190) NOT NULL,
    creado  VARCHAR(30) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS punto_marcado (
    espacio_id    INT NOT NULL,
    punto         VARCHAR(40) NOT NULL,
    marcado_en    VARCHAR(30) NOT NULL,
    vence_manual  VARCHAR(30),
    marcado_por   VARCHAR(190) NOT NULL DEFAULT '',
    PRIMARY KEY (espacio_id, punto),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ajuste (
    espacio_id  INT NOT NULL,
    clave       VARCHAR(190) NOT NULL,
    valor       TEXT NOT NULL,
    PRIMARY KEY (espacio_id, clave),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS aplicabilidad (
    espacio_id   INT NOT NULL,
    control      VARCHAR(40) NOT NULL,
    aplica       TINYINT NOT NULL,
    porque       TEXT NOT NULL,
    decidido_en  VARCHAR(30) NOT NULL,
    PRIMARY KEY (espacio_id, control),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cambio_aplicabilidad (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    espacio_id  INT NOT NULL,
    control     VARCHAR(40) NOT NULL,
    fecha       VARCHAR(30) NOT NULL,
    antes       VARCHAR(40) NOT NULL,
    ahora       VARCHAR(40) NOT NULL,
    motivo      TEXT NOT NULL,
    quien       VARCHAR(190) NOT NULL DEFAULT '',
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sistema (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    espacio_id       INT NOT NULL,
    nombre           VARCHAR(190) NOT NULL,
    tipo             VARCHAR(40) NOT NULL,
    para_que         TEXT NOT NULL,
    datos            TEXT NOT NULL,
    herramientas     TEXT NOT NULL,
    infraestructura  TEXT NOT NULL,
    personas         TEXT NOT NULL,
    actualizado_en   VARCHAR(30) NOT NULL,
    retirado_en      VARCHAR(30),
    UNIQUE (espacio_id, nombre),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS punto_sistema (
    espacio_id    INT NOT NULL,
    punto         VARCHAR(40) NOT NULL,
    sistema_id    INT NOT NULL,
    marcado_en    VARCHAR(30) NOT NULL,
    vence_manual  VARCHAR(30),
    marcado_por   VARCHAR(190) NOT NULL DEFAULT '',
    PRIMARY KEY (espacio_id, punto, sistema_id),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id),
    FOREIGN KEY (sistema_id) REFERENCES sistema(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recordatorio (
    espacio_id      INT NOT NULL,
    requisito       VARCHAR(40) NOT NULL,
    meses           INT NOT NULL,
    desde           VARCHAR(30) NOT NULL,
    hecho_en        VARCHAR(30),
    proximo_manual  VARCHAR(30),
    PRIMARY KEY (espacio_id, requisito),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS plazo (
    espacio_id  INT NOT NULL,
    requisito   VARCHAR(40) NOT NULL,
    meses       INT,
    PRIMARY KEY (espacio_id, requisito),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS actividad (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    espacio_id  INT NOT NULL,
    cuando      VARCHAR(30) NOT NULL,
    accion      VARCHAR(40) NOT NULL,
    requisito   VARCHAR(40),
    punto       VARCHAR(40),
    sistema     VARCHAR(190),
    detalle     TEXT NOT NULL,
    quien       VARCHAR(190) NOT NULL DEFAULT '',
    KEY (espacio_id, requisito),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS nota (
    espacio_id   INT NOT NULL,
    requisito    VARCHAR(40) NOT NULL,
    texto        MEDIUMTEXT NOT NULL,
    actualizada  VARCHAR(30) NOT NULL,
    PRIMARY KEY (espacio_id, requisito),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS propuesta (
    espacio_id   INT NOT NULL,
    control      VARCHAR(40) NOT NULL,
    decision     VARCHAR(20) NOT NULL,
    porque       TEXT NOT NULL,
    apoyo        TEXT NOT NULL,
    contestado   TEXT NOT NULL,
    quien        VARCHAR(20) NOT NULL DEFAULT 'ia',
    aviso        TEXT NOT NULL,
    creada       VARCHAR(30) NOT NULL,
    PRIMARY KEY (espacio_id, control),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS borrador_ia (
    espacio_id  INT NOT NULL,
    documento   VARCHAR(190) NOT NULL,
    huella      VARCHAR(190) NOT NULL,
    texto       MEDIUMTEXT NOT NULL,
    creado      VARCHAR(30) NOT NULL,
    PRIMARY KEY (espacio_id, documento),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pregunta_ia (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    espacio_id  INT NOT NULL,
    documento   VARCHAR(190) NOT NULL,
    texto       TEXT NOT NULL,
    respuesta   TEXT NOT NULL,
    creada      VARCHAR(30) NOT NULL,
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS revision (
    espacio_id   INT NOT NULL,
    punto        VARCHAR(40) NOT NULL,
    sistema_id   INT NOT NULL DEFAULT 0,
    veredicto    VARCHAR(10) NOT NULL,
    porque       TEXT NOT NULL,
    apoyo        TEXT NOT NULL,
    falta        TEXT NOT NULL,
    huella       VARCHAR(190) NOT NULL,
    creada       VARCHAR(30) NOT NULL,
    PRIMARY KEY (espacio_id, punto, sistema_id),
    FOREIGN KEY (espacio_id) REFERENCES espacio(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

# Las tablas de lo que rellena cada empresa, en el orden en que se pueden borrar (las que apuntan a otras, antes)
TABLAS = ("punto_marcado", "ajuste", "aplicabilidad", "cambio_aplicabilidad", "punto_sistema", "recordatorio", "plazo",
          "actividad", "nota", "propuesta", "borrador_ia", "pregunta_ia", "revision", "sistema")

# El espacio que existe siempre; en la v1 es el único
GENERAL = ("general", "General")

# Un nombre repetido (un sistema que ya existe), en SQLite y en el MySQL
REPETIDO = (sqlite3.IntegrityError, pymysql.err.IntegrityError)

# El MySQL, si el portal es el de verdad; None, en local. Lo pone `usar_servidor` al arrancar.
_servidor: srv.Servidor | None = None


def usar_servidor(servidor: srv.Servidor | None) -> None:
    global _servidor
    _servidor = servidor


def en_servidor() -> bool:
    return _servidor is not None


# Con el MySQL, cada consulta es un viaje a Irlanda y vuelta (unos 40 ms): las lecturas que no dependen unas de otras
# van a la vez, cada una por su conexión. Los hilos se quedan, y con ellos sus conexiones.
_a_la_vez = ThreadPoolExecutor(max_workers=8, thread_name_prefix="lecturas")


def a_la_vez(*lecturas: Callable[[], object]) -> list:
    """Lo que devuelve cada lectura, en el mismo orden. En local, una tras otra (no hace falta). Solo para leer: cada
    una va por otra conexión, así que no ve lo que se esté guardando a medias en esta."""
    if _servidor is None or len(lecturas) < 2:
        return [leer() for leer in lecturas]
    # Cada una con lo de esta petición (quién está dentro, en qué empresa), que los hilos no heredan solos
    return [f.result() for f in [_a_la_vez.submit(contextvars.copy_context().run, leer) for leer in lecturas]]


def preparar_servidor(nombre: str, esquema: str) -> None:
    """Crea en el MySQL las tablas que falten (una vez por arranque)."""
    srv.preparar(_servidor, nombre, esquema)


def ahora_utc() -> str:
    """La fecha y hora de ahora como la apuntaba SQLite por su cuenta (en UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def conectar(ruta: Path) -> sqlite3.Connection:
    """En local, el archivo de la empresa; en el MySQL, la conexión de siempre (la ruta solo dice qué empresa es)."""
    if _servidor is not None:
        return srv.conectar(_servidor)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def slug_espacio(ruta: Path) -> str:
    """El espacio de la empresa de esta ruta: en local, el único que hay; en el MySQL, el de su carpeta."""
    return ruta.parent.name if _servidor is not None else GENERAL[0]


def el_espacio(ruta: Path) -> sqlite3.Row | None:
    return espacio(ruta, slug_espacio(ruta))


def iniciar(ruta: Path) -> None:
    """Crea la base de datos si no existe y se asegura de que está el espacio de la empresa.

    Se puede llamar en cada arranque: no duplica nada.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if _servidor is not None:
        preparar_servidor("datos", ESQUEMA_MYSQL)
        with conectar(ruta) as con:
            con.execute("INSERT OR IGNORE INTO espacio (slug, nombre, creado) VALUES (?, ?, ?)",
                        (slug_espacio(ruta), slug_espacio(ruta), ahora_utc()))
        return
    with conectar(ruta) as con:
        con.executescript(ESQUEMA)
        # Bases de datos antiguas: se les añade la columna sin perder lo marcado
        columnas = {c["name"] for c in con.execute("PRAGMA table_info(punto_marcado)")}
        if "vence_manual" not in columnas:
            con.execute("ALTER TABLE punto_marcado ADD COLUMN vence_manual TEXT")
        # Y las de antes de la Declaración mixta: las propuestas que había eran todas de la IA
        columnas = {c["name"] for c in con.execute("PRAGMA table_info(propuesta)")}
        if "quien" not in columnas:
            con.execute("ALTER TABLE propuesta ADD COLUMN quien TEXT NOT NULL DEFAULT 'ia' "
                        "CHECK (quien IN ('portal', 'ia'))")
        if "aviso" not in columnas:
            con.execute("ALTER TABLE propuesta ADD COLUMN aviso TEXT NOT NULL DEFAULT ''")
        # Y las de antes de saber quién hizo cada cosa: lo de antes queda sin nombre
        for tabla, columna in (("punto_marcado", "marcado_por"), ("punto_sistema", "marcado_por"),
                               ("cambio_aplicabilidad", "quien"), ("actividad", "quien")):
            if columna not in {c["name"] for c in con.execute(f"PRAGMA table_info({tabla})")}:
                con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} TEXT NOT NULL DEFAULT ''")
        con.execute("INSERT OR IGNORE INTO espacio (slug, nombre, creado) VALUES (?, ?, ?)", (*GENERAL, ahora_utc()))
    con.close()


def borrar_espacio(ruta: Path) -> None:
    """Todo lo de una empresa en el MySQL, para siempre (al borrarla). En local basta con borrar su carpeta."""
    if _servidor is None:
        return
    with conectar(ruta) as con:
        fila = con.execute("SELECT id FROM espacio WHERE slug = ?", (slug_espacio(ruta),)).fetchone()
        if fila is not None:
            for tabla in TABLAS:
                con.execute(f"DELETE FROM {tabla} WHERE espacio_id = ?", (fila["id"],))
            con.execute("DELETE FROM espacio WHERE id = ?", (fila["id"],))


def espacios(ruta: Path) -> list[sqlite3.Row]:
    con = conectar(ruta)
    try:
        return con.execute("SELECT * FROM espacio ORDER BY id").fetchall()
    finally:
        con.close()


def espacio(ruta: Path, slug: str) -> sqlite3.Row | None:
    con = conectar(ruta)
    try:
        return con.execute("SELECT * FROM espacio WHERE slug = ?", (slug,)).fetchone()
    finally:
        con.close()


def marcados(ruta: Path, espacio_id: int) -> set[str]:
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT punto FROM punto_marcado WHERE espacio_id = ?", (espacio_id,))
        return {f["punto"] for f in filas}
    finally:
        con.close()


@dataclass
class Marca:
    """Un punto marcado a mano: cuándo se cumplió (o renovó), si se recolocó, cuándo vence, y quién lo marcó."""
    desde: date
    vence_manual: date | None = None
    quien: str = ""


def marcas(ruta: Path, espacio_id: int) -> dict[str, Marca]:
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT punto, marcado_en, vence_manual, marcado_por FROM punto_marcado "
                            "WHERE espacio_id = ?", (espacio_id,))
        return {f["punto"]: Marca(date.fromisoformat(f["marcado_en"][:10]),
                                  date.fromisoformat(f["vence_manual"]) if f["vence_manual"] else None,
                                  f["marcado_por"])
                for f in filas}
    finally:
        con.close()


def _una_orden(ruta: Path, sql: str, valores: tuple) -> None:
    """Una sola orden que se guarda al momento. Con el MySQL, sin abrir y cerrar un «guardar de una vez»: son dos
    viajes menos."""
    con = conectar(ruta)
    try:
        con.execute(sql, valores)
        con.commit()
    finally:
        con.close()


def marcar(ruta: Path, espacio_id: int, punto: str, hoy: date, quien: str = "") -> None:
    _una_orden(ruta, "INSERT OR IGNORE INTO punto_marcado (espacio_id, punto, marcado_en, marcado_por) "
                     "VALUES (?, ?, ?, ?)", (espacio_id, punto, hoy.isoformat(), quien))


def renovar(ruta: Path, espacio_id: int, punto: str, hoy: date, quien: str = "") -> None:
    """La fecha nueva cuenta desde hoy y se olvida la recolocada. Queda a nombre de quien renueva."""
    with conectar(ruta) as con:
        con.execute("UPDATE punto_marcado SET marcado_en = ?, vence_manual = NULL, marcado_por = ? "
                    "WHERE espacio_id = ? AND punto = ?", (hoy.isoformat(), quien, espacio_id, punto))
    con.close()


def recolocar(ruta: Path, espacio_id: int, punto: str, vence: date | None) -> None:
    """Fija a mano la fecha de vencimiento de un punto; con None vuelve a la calculada."""
    with conectar(ruta) as con:
        con.execute("UPDATE punto_marcado SET vence_manual = ? WHERE espacio_id = ? AND punto = ?",
                    (vence.isoformat() if vence else None, espacio_id, punto))
    con.close()


def desmarcar(ruta: Path, espacio_id: int, punto: str) -> None:
    _una_orden(ruta, "DELETE FROM punto_marcado WHERE espacio_id = ? AND punto = ?", (espacio_id, punto))


def nota(ruta: Path, espacio_id: int, requisito: str) -> str:
    con = conectar(ruta)
    try:
        fila = con.execute("SELECT texto FROM nota WHERE espacio_id = ? AND requisito = ?",
                           (espacio_id, requisito)).fetchone()
        return fila["texto"] if fila else ""
    finally:
        con.close()


def guardar_nota(ruta: Path, espacio_id: int, requisito: str, texto: str) -> None:
    """Guarda la nota; si queda vacía, la borra."""
    with conectar(ruta) as con:
        if texto.strip():
            con.execute(
                "INSERT INTO nota (espacio_id, requisito, texto, actualizada) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (espacio_id, requisito) "
                "DO UPDATE SET texto = excluded.texto, actualizada = excluded.actualizada",
                (espacio_id, requisito, texto.strip(), ahora_utc()))
        else:
            con.execute("DELETE FROM nota WHERE espacio_id = ? AND requisito = ?", (espacio_id, requisito))
    con.close()


def ajuste(ruta: Path, espacio_id: int, clave: str, defecto: str) -> str:
    con = conectar(ruta)
    try:
        fila = con.execute("SELECT valor FROM ajuste WHERE espacio_id = ? AND clave = ?",
                           (espacio_id, clave)).fetchone()
        return fila["valor"] if fila else defecto
    finally:
        con.close()


def ajustes(ruta: Path, espacio_id: int) -> dict[str, str]:
    """Todos los ajustes del espacio de una vez (el cuestionario son unos 30)."""
    con = conectar(ruta)
    try:
        return {f["clave"]: f["valor"] for f in con.execute("SELECT clave, valor FROM ajuste WHERE espacio_id = ?",
                                                             (espacio_id,))}
    finally:
        con.close()


def guardar_ajuste(ruta: Path, espacio_id: int, clave: str, valor: str) -> None:
    with conectar(ruta) as con:
        con.execute("INSERT INTO ajuste (espacio_id, clave, valor) VALUES (?, ?, ?) "
                    "ON CONFLICT (espacio_id, clave) DO UPDATE SET valor = excluded.valor",
                    (espacio_id, clave, valor))
    con.close()


def reservar_ajuste(ruta: Path, espacio_id: int, clave: str, antes: str, ahora: str) -> bool:
    """Cambia un ajuste solo si sigue valiendo `antes`, y dice si lo ha cambiado. Si dos ordenadores lo intentan a la
    vez, solo uno lo consigue: así un aviso no sale repetido.

    Son dos órdenes sueltas, sin «guardar de una vez»: la primera deja la fila con el valor de antes si no estaba, y la
    segunda, que es una sola orden, la cambia solo si nadie lo ha hecho antes. Juntas en una, el MySQL se atascaba
    cuando varios lo intentaban a la vez."""
    con = conectar(ruta)
    try:
        con.execute("INSERT OR IGNORE INTO ajuste (espacio_id, clave, valor) VALUES (?, ?, ?)", (espacio_id, clave, antes))
        cambiadas = con.execute("UPDATE ajuste SET valor = ? WHERE espacio_id = ? AND clave = ? AND valor = ?",
                                (ahora, espacio_id, clave, antes)).rowcount
        con.commit()
        return cambiadas == 1
    finally:
        con.close()


def plazos(ruta: Path, espacio_id: int) -> dict[str, int | None]:
    """Solo los plazos cambiados en ajustes; los demás usan el de por defecto."""
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT requisito, meses FROM plazo WHERE espacio_id = ?", (espacio_id,))
        return {f["requisito"]: f["meses"] for f in filas}
    finally:
        con.close()


def guardar_plazo(ruta: Path, espacio_id: int, requisito: str, meses: int | None) -> None:
    with conectar(ruta) as con:
        con.execute("INSERT INTO plazo (espacio_id, requisito, meses) VALUES (?, ?, ?) "
                    "ON CONFLICT (espacio_id, requisito) DO UPDATE SET meses = excluded.meses",
                    (espacio_id, requisito, meses))
    con.close()


def borrar_plazos(ruta: Path, espacio_id: int) -> None:
    """Todos los requisitos vuelven a su plazo por defecto."""
    with conectar(ruta) as con:
        con.execute("DELETE FROM plazo WHERE espacio_id = ?", (espacio_id,))
    con.close()


@dataclass
class Decision:
    aplica: bool
    porque: str
    fecha: date


def decisiones(ruta: Path, espacio_id: int) -> dict[str, Decision]:
    """Los controles decididos; los que no están, sin decidir."""
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT control, aplica, porque, decidido_en FROM aplicabilidad WHERE espacio_id = ?",
                            (espacio_id,))
        return {f["control"]: Decision(bool(f["aplica"]), f["porque"], date.fromisoformat(f["decidido_en"]))
                for f in filas}
    finally:
        con.close()


def _texto(aplica: bool | None) -> str:
    return "sin decidir" if aplica is None else "aplica" if aplica else "no aplica"


def decidir(ruta: Path, espacio_id: int, control: str, aplica: bool, porque: str, motivo: str, hoy: date,
            quien: str = "") -> None:
    """Guarda la decisión y, si cambia (o es la primera), la apunta en los cambios.

    Las comprobaciones (porqué y motivo obligatorios) las hace quien llama.
    """
    with conectar(ruta) as con:
        fila = con.execute("SELECT aplica FROM aplicabilidad WHERE espacio_id = ? AND control = ?",
                           (espacio_id, control)).fetchone()
        antes = None if fila is None else bool(fila["aplica"])
        con.execute("INSERT INTO aplicabilidad (espacio_id, control, aplica, porque, decidido_en) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (espacio_id, control) DO UPDATE SET "
                    "decidido_en = CASE WHEN aplica = excluded.aplica THEN decidido_en ELSE excluded.decidido_en END, "
                    "aplica = excluded.aplica, porque = excluded.porque",
                    (espacio_id, control, int(aplica), porque, hoy.isoformat()))
        if antes != aplica:
            con.execute("INSERT INTO cambio_aplicabilidad (espacio_id, control, fecha, antes, ahora, motivo, quien) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (espacio_id, control, hoy.isoformat(), _texto(antes), _texto(aplica), motivo or porque, quien))
    con.close()


SIN_DECIDIR = "Se deja sin decidir"


def quitar_decision(ruta: Path, espacio_id: int, control: str, hoy: date, quien: str = "") -> bool:
    """Vuelve un control a «sin decidir» (se desmarca la opción elegida) y lo apunta en los cambios. Dice si estaba
    decidido."""
    with conectar(ruta) as con:
        fila = con.execute("SELECT aplica FROM aplicabilidad WHERE espacio_id = ? AND control = ?",
                           (espacio_id, control)).fetchone()
        if fila is not None:
            con.execute("DELETE FROM aplicabilidad WHERE espacio_id = ? AND control = ?", (espacio_id, control))
            con.execute("INSERT INTO cambio_aplicabilidad (espacio_id, control, fecha, antes, ahora, motivo, quien) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (espacio_id, control, hoy.isoformat(), _texto(bool(fila["aplica"])), _texto(None), SIN_DECIDIR,
                         quien))
    con.close()
    return fila is not None


def corregir_motivo(ruta: Path, espacio_id: int, control: str, viejo: str, nuevo: str, hoy: date) -> None:
    """Mientras se escribe el porqué de un cambio, el último cambio del control lleva el texto final y no
    el que había a medias: solo si es de hoy y su motivo era ese texto."""
    with conectar(ruta) as con:
        fila = con.execute("SELECT id, fecha, motivo FROM cambio_aplicabilidad WHERE espacio_id = ? AND control = ? "
                           "ORDER BY id DESC LIMIT 1", (espacio_id, control)).fetchone()
        if fila and fila["fecha"] == hoy.isoformat() and fila["motivo"] == viejo:
            con.execute("UPDATE cambio_aplicabilidad SET motivo = ? WHERE id = ?", (nuevo, fila["id"]))
    con.close()


def cambios(ruta: Path, espacio_id: int) -> list[sqlite3.Row]:
    """Los cambios de la Declaración, el más reciente primero."""
    con = conectar(ruta)
    try:
        return con.execute("SELECT * FROM cambio_aplicabilidad WHERE espacio_id = ? ORDER BY id DESC",
                           (espacio_id,)).fetchall()
    finally:
        con.close()


# --- Inventario de IA ---

TIPOS = {"producto": "La ofrecemos a clientes", "herramienta": "La usa el equipo"}
CAMPOS = ("para_que", "datos", "herramientas", "infraestructura", "personas")


class NombreRepetido(Exception):
    pass


@dataclass
class Sistema:
    id: int
    nombre: str
    tipo: str
    para_que: str
    datos: str
    herramientas: str
    infraestructura: str
    personas: str
    actualizado: date
    retirado: date | None

    def campo(self, nombre: str) -> str:
        return getattr(self, nombre)

    @property
    def completos(self) -> int:
        return sum(bool(self.campo(c).strip()) for c in CAMPOS)


def _sistema(f) -> Sistema:
    return Sistema(f["id"], f["nombre"], f["tipo"], f["para_que"], f["datos"], f["herramientas"],
                   f["infraestructura"], f["personas"], date.fromisoformat(f["actualizado_en"]),
                   date.fromisoformat(f["retirado_en"]) if f["retirado_en"] else None)


def sistemas(ruta: Path, espacio_id: int) -> list[Sistema]:
    """Todos, también los retirados, por orden de nombre."""
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT * FROM sistema WHERE espacio_id = ? ORDER BY nombre COLLATE NOCASE",
                            (espacio_id,))
        return [_sistema(f) for f in filas]
    finally:
        con.close()


def sistema(ruta: Path, espacio_id: int, sistema_id: int) -> Sistema | None:
    con = conectar(ruta)
    try:
        f = con.execute("SELECT * FROM sistema WHERE espacio_id = ? AND id = ?", (espacio_id, sistema_id)).fetchone()
        return _sistema(f) if f else None
    finally:
        con.close()


def crear_sistema(ruta: Path, espacio_id: int, nombre: str, tipo: str, hoy: date) -> int:
    try:
        with conectar(ruta) as con:
            cur = con.execute("INSERT INTO sistema (espacio_id, nombre, tipo, para_que, datos, herramientas, "
                              "infraestructura, personas, actualizado_en) VALUES (?, ?, ?, '', '', '', '', '', ?)",
                              (espacio_id, nombre, tipo, hoy.isoformat()))
            nuevo = cur.lastrowid
    except REPETIDO:
        raise NombreRepetido(nombre)
    finally:
        con.close()
    return nuevo


def guardar_sistema(ruta: Path, espacio_id: int, sistema_id: int, nombre: str, tipo: str,
                    campos: dict[str, str], hoy: date) -> None:
    try:
        with conectar(ruta) as con:
            con.execute(f"UPDATE sistema SET nombre = ?, tipo = ?, {', '.join(f'{c} = ?' for c in CAMPOS)}, "
                        "actualizado_en = ? WHERE espacio_id = ? AND id = ?",
                        (nombre, tipo, *(campos.get(c, "") for c in CAMPOS), hoy.isoformat(), espacio_id, sistema_id))
    except REPETIDO:
        raise NombreRepetido(nombre)
    finally:
        con.close()


def retirar_sistema(ruta: Path, espacio_id: int, sistema_id: int, hoy: date | None) -> None:
    """Con una fecha lo retira; con None lo vuelve a activar."""
    with conectar(ruta) as con:
        con.execute("UPDATE sistema SET retirado_en = ? WHERE espacio_id = ? AND id = ?",
                    (hoy.isoformat() if hoy else None, espacio_id, sistema_id))
    con.close()


# --- Marcas por sistema: una por punto y sistema ---

def marcas_sistema(ruta: Path, espacio_id: int) -> dict[tuple[str, int], Marca]:
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT punto, sistema_id, marcado_en, vence_manual, marcado_por FROM punto_sistema "
                            "WHERE espacio_id = ?", (espacio_id,))
        return {(f["punto"], f["sistema_id"]): Marca(date.fromisoformat(f["marcado_en"][:10]),
                                                     date.fromisoformat(f["vence_manual"]) if f["vence_manual"] else None,
                                                     f["marcado_por"])
                for f in filas}
    finally:
        con.close()


def marcar_linea(ruta: Path, espacio_id: int, punto: str, sistema_id: int, hoy: date, quien: str = "") -> None:
    _una_orden(ruta, "INSERT OR IGNORE INTO punto_sistema (espacio_id, punto, sistema_id, marcado_en, marcado_por) "
                     "VALUES (?, ?, ?, ?, ?)", (espacio_id, punto, sistema_id, hoy.isoformat(), quien))


def desmarcar_linea(ruta: Path, espacio_id: int, punto: str, sistema_id: int) -> None:
    _una_orden(ruta, "DELETE FROM punto_sistema WHERE espacio_id = ? AND punto = ? AND sistema_id = ?",
               (espacio_id, punto, sistema_id))


def renovar_linea(ruta: Path, espacio_id: int, punto: str, sistema_id: int, hoy: date, quien: str = "") -> None:
    with conectar(ruta) as con:
        con.execute("UPDATE punto_sistema SET marcado_en = ?, vence_manual = NULL, marcado_por = ? "
                    "WHERE espacio_id = ? AND punto = ? AND sistema_id = ?",
                    (hoy.isoformat(), quien, espacio_id, punto, sistema_id))
    con.close()


def recolocar_linea(ruta: Path, espacio_id: int, punto: str, sistema_id: int, vence: date | None) -> None:
    with conectar(ruta) as con:
        con.execute("UPDATE punto_sistema SET vence_manual = ? WHERE espacio_id = ? AND punto = ? AND sistema_id = ?",
                    (vence.isoformat() if vence else None, espacio_id, punto, sistema_id))
    con.close()


# --- Recordatorios intermedios ---

@dataclass
class Recordatorio:
    meses: int
    desde: date
    hecho: date | None = None


def _fecha(texto: str | None) -> date | None:
    return date.fromisoformat(texto) if texto else None


def recordatorios(ruta: Path, espacio_id: int) -> dict[str, Recordatorio]:
    con = conectar(ruta)
    try:
        filas = con.execute("SELECT * FROM recordatorio WHERE espacio_id = ?", (espacio_id,))
        return {f["requisito"]: Recordatorio(f["meses"], date.fromisoformat(f["desde"]), _fecha(f["hecho_en"]))
                for f in filas}
    finally:
        con.close()


def guardar_recordatorio(ruta: Path, espacio_id: int, requisito: str, meses: int | None, hoy: date) -> None:
    """Con meses, lo pone (o cambia cada cuánto, y vuelve a contar desde hoy); con None, «sin
    recordatorio» (se guarda como 0, para que no vuelva el de por defecto)."""
    with conectar(ruta) as con:
        con.execute("INSERT INTO recordatorio (espacio_id, requisito, meses, desde) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT (espacio_id, requisito) DO UPDATE SET meses = excluded.meses, "
                    "desde = excluded.desde",
                    (espacio_id, requisito, meses or 0, hoy.isoformat()))
    con.close()


def recordatorio_hecho(ruta: Path, espacio_id: int, requisito: str, meses: int, hoy: date) -> None:
    """Si el recordatorio era el de por defecto, aquí se guarda por primera vez, con sus meses."""
    with conectar(ruta) as con:
        con.execute("INSERT INTO recordatorio (espacio_id, requisito, meses, desde, hecho_en) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (espacio_id, requisito) DO UPDATE SET hecho_en = excluded.hecho_en",
                    (espacio_id, requisito, meses, hoy.isoformat(), hoy.isoformat()))
    con.close()


def borrar_recordatorios(ruta: Path, espacio_id: int) -> None:
    """Todos vuelven a su recordatorio por defecto."""
    with conectar(ruta) as con:
        con.execute("DELETE FROM recordatorio WHERE espacio_id = ?", (espacio_id,))
    con.close()


# --- Actividad ---

# Quien firma lo que el portal hace solo (los avisos de la tarea de Windows), en «Actividad»
EL_PORTAL = "el portal"


def apuntar(ruta: Path, espacio_id: int, cuando: datetime, accion: str, *, requisito: str | None = None,
            punto: str | None = None, sistema: str | None = None, detalle: str = "", quien: str = "") -> None:
    _una_orden(ruta, "INSERT INTO actividad (espacio_id, cuando, accion, requisito, punto, sistema, detalle, quien) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
               (espacio_id, cuando.isoformat(timespec="seconds"), accion, requisito, punto, sistema, detalle, quien))


def corregir_actividad(ruta: Path, fila_id: int, cuando: datetime, detalle: str) -> None:
    """Pone al día una línea ya apuntada en vez de añadir otra (el porqué que se sigue escribiendo)."""
    with conectar(ruta) as con:
        con.execute("UPDATE actividad SET cuando = ?, detalle = ? WHERE id = ?",
                    (cuando.isoformat(timespec="seconds"), detalle, fila_id))
    con.close()


def actividad(ruta: Path, espacio_id: int, requisito: str | None = None) -> list[sqlite3.Row]:
    """Lo más reciente primero; con requisito, solo lo suyo."""
    con = conectar(ruta)
    try:
        if requisito:
            filas = con.execute("SELECT * FROM actividad WHERE espacio_id = ? AND requisito = ? ORDER BY id DESC",
                                (espacio_id, requisito))
        else:
            filas = con.execute("SELECT * FROM actividad WHERE espacio_id = ? ORDER BY id DESC", (espacio_id,))
        return filas.fetchall()
    finally:
        con.close()


# --- Borradores con IA ---

def borrador_ia(ruta: Path, espacio_id: int, documento: str) -> sqlite3.Row | None:
    con = conectar(ruta)
    try:
        return con.execute("SELECT * FROM borrador_ia WHERE espacio_id = ? AND documento = ?",
                           (espacio_id, documento)).fetchone()
    finally:
        con.close()


def guardar_borrador_ia(ruta: Path, espacio_id: int, documento: str, huella: str, texto: str, hoy: date) -> None:
    with conectar(ruta) as con:
        con.execute("INSERT INTO borrador_ia (espacio_id, documento, huella, texto, creado) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (espacio_id, documento) DO UPDATE SET huella = excluded.huella, texto = excluded.texto, "
                    "creado = excluded.creado", (espacio_id, documento, huella, texto, hoy.isoformat()))
    con.close()


def preguntas_ia(ruta: Path, espacio_id: int) -> list[sqlite3.Row]:
    con = conectar(ruta)
    try:
        return con.execute("SELECT * FROM pregunta_ia WHERE espacio_id = ? ORDER BY id", (espacio_id,)).fetchall()
    finally:
        con.close()


def poner_preguntas_ia(ruta: Path, espacio_id: int, documento: str, textos: list[str], hoy: date) -> None:
    """Las preguntas nuevas de un borrador sustituyen a las suyas sin contestar; las contestadas se quedan. No se
    repite una que ya esté (de cualquier borrador)."""
    with conectar(ruta) as con:
        con.execute("DELETE FROM pregunta_ia WHERE espacio_id = ? AND documento = ? AND respuesta = ''",
                    (espacio_id, documento))
        hay = {" ".join(f["texto"].split()).casefold()
               for f in con.execute("SELECT texto FROM pregunta_ia WHERE espacio_id = ?", (espacio_id,))}
        for t in textos:
            if " ".join(t.split()).casefold() not in hay:
                con.execute("INSERT INTO pregunta_ia (espacio_id, documento, texto, respuesta, creada) "
                            "VALUES (?, ?, ?, '', ?)",
                            (espacio_id, documento, t, hoy.isoformat()))
                hay.add(" ".join(t.split()).casefold())
    con.close()


def contestar_pregunta_ia(ruta: Path, espacio_id: int, pregunta_id: int, respuesta: str) -> sqlite3.Row | None:
    """Guarda la respuesta y devuelve la pregunta; None si no es de este espacio."""
    with conectar(ruta) as con:
        fila = con.execute("SELECT * FROM pregunta_ia WHERE espacio_id = ? AND id = ?",
                           (espacio_id, pregunta_id)).fetchone()
        if fila is not None:
            con.execute("UPDATE pregunta_ia SET respuesta = ? WHERE id = ?", (respuesta.strip(), pregunta_id))
    con.close()
    return fila


# --- Propuestas de la IA para la Declaración ---

def propuestas(ruta: Path, espacio_id: int) -> dict[str, sqlite3.Row]:
    con = conectar(ruta)
    try:
        return {f["control"]: f for f in con.execute("SELECT * FROM propuesta WHERE espacio_id = ?", (espacio_id,))}
    finally:
        con.close()


def guardar_propuesta(ruta: Path, espacio_id: int, control: str, decision: str, porque: str, apoyo: str,
                      contestado: str = "", quien: str = "ia", aviso: str = "") -> None:
    with conectar(ruta) as con:
        con.execute("INSERT INTO propuesta (espacio_id, control, decision, porque, apoyo, contestado, quien, aviso, "
                    "creada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT (espacio_id, control) DO UPDATE SET decision = excluded.decision, porque = excluded.porque, "
                    "apoyo = excluded.apoyo, contestado = excluded.contestado, quien = excluded.quien, "
                    "aviso = excluded.aviso, creada = excluded.creada",
                    (espacio_id, control, decision, porque, apoyo, contestado, quien, aviso, ahora_utc()))
    con.close()


def quitar_propuesta(ruta: Path, espacio_id: int, control: str) -> None:
    with conectar(ruta) as con:
        con.execute("DELETE FROM propuesta WHERE espacio_id = ? AND control = ?", (espacio_id, control))
    con.close()


# --- Revisiones de la IA de los archivos ---

def revisiones(ruta: Path, espacio_id: int, puntos: list[str]) -> dict[tuple[str, int], sqlite3.Row]:
    """Las de unos puntos: {(punto, sistema_id): fila}."""
    con = conectar(ruta)
    try:
        filas = con.execute(f"SELECT * FROM revision WHERE espacio_id = ? AND punto IN ({','.join('?' * len(puntos))})",
                            (espacio_id, *puntos)) if puntos else []
        return {(f["punto"], f["sistema_id"]): f for f in filas}
    finally:
        con.close()


def guardar_revision(ruta: Path, espacio_id: int, punto: str, sistema_id: int, veredicto: str, porque: str,
                     apoyo: str, falta: str, huella: str, cuando: datetime) -> None:
    with conectar(ruta) as con:
        con.execute("INSERT OR REPLACE INTO revision (espacio_id, punto, sistema_id, veredicto, porque, apoyo, falta, "
                    "huella, creada) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (espacio_id, punto, sistema_id, veredicto, porque, apoyo, falta, huella,
                     cuando.isoformat(timespec="minutes")))
    con.close()

