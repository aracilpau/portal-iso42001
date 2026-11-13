# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Importar el portal de otra persona a una empresa: su `portal.db` y su carpeta de pruebas.

El `portal.db` puede ser de una versión anterior: se copia a una carpeta temporal y se pone al día como hace el portal
al arrancar, sin tocar el original. Después todo pasa, de una vez, al espacio de la empresa de destino (en el MySQL o
en local): si algo falla a mitad, no queda nada a medias. Los sistemas cambian de número al entrar, así que lo que
los nombra por número (las marcas por sistema, las revisiones y las altas pendientes) se renumera.

Solo se importa a una empresa vacía, para no mezclar. Lo que en el original no dice quién lo hizo (lo de antes de los
usuarios) queda a nombre de quien se diga.
"""
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from portal import db

# Las que tienen número propio: al entrar en el destino se les da otro
CON_ID = {"sistema", "actividad", "cambio_aplicabilidad", "pregunta_ia"}
# Dónde se apunta quién hizo cada cosa; «propuesta.quien» no es una persona («ia» o «portal»)
QUIEN = {"punto_marcado": "marcado_por", "punto_sistema": "marcado_por", "actividad": "quien",
         "cambio_aplicabilidad": "quien"}


class ErrorImportar(Exception):
    pass


@dataclass
class Resumen:
    filas: dict[str, int] = field(default_factory=dict)  # tabla → cuántas filas
    archivos: int = 0

    def texto(self) -> str:
        lineas = [f"  {t}: {n}" for t, n in self.filas.items() if n]
        return "\n".join(lineas + [f"  archivos: {self.archivos}"])


def _leer(origen: Path) -> tuple[dict[str, list[dict]], str]:
    """Las filas del portal de origen, ya puesto al día (en una copia), y cuándo se creó su espacio."""
    with tempfile.TemporaryDirectory() as carpeta:
        copia = Path(carpeta) / "portal.db"
        shutil.copy2(origen, copia)
        servidor = db._servidor
        db.usar_servidor(None)  # la copia es SQLite, aunque el destino sea el MySQL
        try:
            db.iniciar(copia)
        finally:
            db.usar_servidor(servidor)
        con = sqlite3.connect(copia)
        con.row_factory = sqlite3.Row
        try:
            espacios = con.execute("SELECT id, creado FROM espacio").fetchall()
            if len(espacios) != 1:
                raise ErrorImportar(f"El portal de origen tiene {len(espacios)} espacios; se espera uno.")
            e = espacios[0]["id"]
            filas = {t: [dict(f) for f in con.execute(f"SELECT * FROM {t} WHERE espacio_id = ? ORDER BY rowid", (e,))]
                     for t in db.TABLAS}
            return filas, espacios[0]["creado"]
        finally:
            con.close()


def _archivos(carpeta: Path) -> list[Path]:
    return [r for r in carpeta.rglob("*") if r.is_file()] if carpeta.is_dir() else []


def importar(origen_bd: Path, origen_pruebas: Path, destino_bd: Path, destino_pruebas: Path,
             quien: str) -> Resumen:
    """Pasa el portal de origen a la empresa de `destino_bd` y sus archivos a `destino_pruebas` (la carpeta de pruebas
    de esa empresa: las de cada requisito van dentro)."""
    if not origen_bd.is_file():
        raise ErrorImportar(f"No se encuentra {origen_bd}.")
    if not origen_pruebas.is_dir():
        raise ErrorImportar(f"No se encuentra la carpeta de pruebas {origen_pruebas}.")
    if _archivos(destino_pruebas):
        raise ErrorImportar(f"La carpeta de pruebas de destino ya tiene archivos ({destino_pruebas}): solo se importa "
                            "a una empresa vacía.")
    filas, creado = _leer(origen_bd)
    destino = db.el_espacio(destino_bd)
    e = destino["id"]
    resumen = Resumen()
    with db.conectar(destino_bd) as con:
        ocupadas = [t for t in db.TABLAS
                    if con.execute(f"SELECT COUNT(*) AS n FROM {t} WHERE espacio_id = ?", (e,)).fetchone()["n"]]
        if ocupadas:
            raise ErrorImportar("La empresa de destino ya tiene datos (" + ", ".join(ocupadas) + "): solo se importa "
                                "a una empresa vacía.")
        numeros = {}  # sistema: número en el origen → número en el destino
        for tabla in ("sistema",) + tuple(t for t in db.TABLAS if t != "sistema"):
            for f in filas[tabla]:
                viejo = f.pop("id", None) if tabla in CON_ID else None
                f["espacio_id"] = e
                if f.get("sistema_id"):  # 0: el punto no va por sistema
                    f["sistema_id"] = numeros[f["sistema_id"]]
                if tabla in QUIEN and not f[QUIEN[tabla]]:
                    f[QUIEN[tabla]] = quien
                if tabla == "ajuste" and f["clave"] == "altas_pendientes" and f["valor"]:
                    f["valor"] = ",".join(f"{numeros[int(n)]}:{como}"
                                          for n, como in (a.split(":") for a in f["valor"].split(",")))
                cur = con.execute(f"INSERT INTO {tabla} ({', '.join(f)}) VALUES ({', '.join('?' * len(f))})",
                                  tuple(f.values()))
                if tabla == "sistema":
                    numeros[viejo] = cur.lastrowid
            resumen.filas[tabla] = len(filas[tabla])
        # El seguimiento cuenta desde que se empezó: si el origen es más antiguo, manda su fecha
        if creado < destino["creado"]:
            con.execute("UPDATE espacio SET creado = ? WHERE id = ?", (creado, e))
    # Los archivos, después: si la base de datos no ha entrado, no se copia nada
    destino_pruebas.mkdir(parents=True, exist_ok=True)
    shutil.copytree(origen_pruebas, destino_pruebas, dirs_exist_ok=True)  # copy2: con su fecha, para las revisiones
    resumen.archivos = len(_archivos(origen_pruebas))
    return resumen
