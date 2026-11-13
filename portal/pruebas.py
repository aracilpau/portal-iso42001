# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Las carpetas de pruebas de cada espacio.

    <raíz>/<espacio>/<requisito>/<punto>/            los archivos de cada punto
    <raíz>/<espacio>/<requisito>/<punto>/<sistema>/  en los puntos por sistema, los de cada sistema
    <raíz>/<espacio>/<requisito>/historial/          lo que se quitó o se sustituyó al renovar

Al retirar un sistema, sus archivos pasan al historial de cada requisito y sus carpetas vacías se
quitan; al volver a activarlo, sus carpetas se crean de nuevo, vacías.

Un control que no aplica lleva la marca en su carpeta, «A.7.3 (no aplica)», con todo lo de dentro; si
vuelve a aplicar, se le quita. El portal la encuentra con marca o sin ella.

La carpeta manda: el portal enseña lo que haya dentro, así que también se pueden meter archivos
desde el Explorador. Las carpetas llevan solo el código, para no renombrar nada si cambia un
título en la guía.
"""
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO

from portal import guia, seguimiento
from portal.db import Sistema

HISTORIAL = "historial"
NO_APLICA = " (no aplica)"
NO_VALEN = '<>:"/\\|?*'


@dataclass
class Archivo:
    nombre: str
    fecha: datetime  # cuándo se guardó por última vez
    bytes: int

    @property
    def tamaño(self) -> str:
        n = self.bytes
        for unidad in ("bytes", "KB", "MB"):
            if n < 1024 or unidad == "MB":
                return f"{n:.0f} {unidad}" if unidad == "bytes" else f"{n:.1f} {unidad}".replace(".", ",")
            n /= 1024


class NoEncontrado(Exception):
    pass


class CarpetaOcupada(Exception):
    """Windows no deja renombrar una carpeta si hay un archivo suyo abierto (p. ej. en Word)."""


def tiene_carpeta(p: guia.Punto) -> bool:
    """Los apoyados no tienen archivos propios: llevan a los de aquel en que se apoyan."""
    return seguimiento.clase(p) != seguimiento.APOYADO


def _con_carpeta_por_sistema(p: guia.Punto) -> bool:
    """Los puntos por sistema con archivos: los que se marcan por sistema (los de la ficha no)."""
    return seguimiento.clase(p) == seguimiento.SISTEMA


def nombre_carpeta(x: Sistema) -> str:
    base = nombre_seguro(x.nombre)
    return f"{base} (retirado {x.retirado:%Y-%m})" if x.retirado else base


def _requisito_de(punto: str) -> str:
    return seguimiento.REQUISITO_DE[punto].codigo


def nombre_seguro(nombre: str) -> str:
    """El nombre con que se guarda un archivo subido: sin carpetas delante ni caracteres que
    Windows no admite."""
    nombre = nombre.replace("\\", "/").rsplit("/", 1)[-1]
    nombre = "".join("_" if c in NO_VALEN or ord(c) < 32 else c for c in nombre).strip(" .")
    return nombre or "archivo"


def _libre(carpeta: Path, nombre: str) -> Path:
    """Si ya hay uno con ese nombre, «nombre (2).pdf», «nombre (3).pdf»… nunca se pisa nada."""
    ruta = carpeta / nombre
    n = 2
    while ruta.exists():
        ruta = carpeta / f"{Path(nombre).stem} ({n}){Path(nombre).suffix}"
        n += 1
    return ruta


def _listar(carpeta: Path) -> list[Archivo]:
    if not carpeta.is_dir():
        return []
    res = []
    for f in carpeta.iterdir():
        # Fuera los temporales de Office (~$…) y los ocultos
        if f.is_file() and not f.name.startswith(("~$", ".")):
            st = f.stat()
            res.append(Archivo(f.name, datetime.fromtimestamp(st.st_mtime), st.st_size))
    return sorted(res, key=lambda a: a.nombre.lower())


def _buscar(carpeta: Path, nombre: str) -> Path:
    """Solo vale el nombre exacto de un archivo que esté en esa carpeta: así nadie se sale de ella
    con nombres como «../../algo»."""
    if carpeta.is_dir() and nombre in {f.name for f in carpeta.iterdir() if f.is_file()}:
        return carpeta / nombre
    raise NoEncontrado(nombre)


class Pruebas:
    """Las carpetas de pruebas de un espacio."""

    def __init__(self, raiz: Path, espacio: str):
        self.base = raiz / espacio
        self.excluidos: set[str] = set()  # los controles que no aplican, para la marca de su carpeta

    def _requisito(self, codigo: str) -> Path:
        """La carpeta de un requisito: con la marca «(no aplica)» si no aplica. Si aún no se ha podido
        poner o quitar (había un archivo abierto), la que haya, para no perder de vista lo de dentro."""
        sin, con = self.base / codigo, self.base / f"{codigo}{NO_APLICA}"
        quiere, otra = (con, sin) if codigo in self.excluidos else (sin, con)
        return otra if otra.is_dir() and not quiere.is_dir() else quiere

    def poner_al_dia(self, excluidos: set[str]) -> list[str]:
        """Pone o quita la marca «(no aplica)» según la Declaración. Devuelve los controles cuya carpeta
        no se ha podido renombrar (un archivo suyo abierto): se vuelve a intentar la próxima vez."""
        self.excluidos = set(excluidos)
        fallan = []
        for r in guia.requisitos():
            sin, con = self.base / r.codigo, self.base / f"{r.codigo}{NO_APLICA}"
            origen, destino = (sin, con) if r.codigo in self.excluidos else (con, sin)
            if origen.is_dir() and not destino.exists():
                try:
                    origen.rename(destino)
                except OSError:
                    fallan.append(r.codigo)
        return fallan

    def crear(self, sistemas: list[Sistema] = ()) -> None:
        """Las carpetas de los 65 requisitos y sus puntos, apliquen o no, y las de cada
        sistema activo en sus puntos por sistema. No toca lo que ya hay."""
        for r in guia.requisitos():
            carpeta = self._requisito(r.codigo)
            carpeta.mkdir(parents=True, exist_ok=True)
            for p in r.puntos:
                if tiene_carpeta(p):
                    (carpeta / p.codigo).mkdir(exist_ok=True)
        for x in sistemas:
            if x.retirado is None:
                self.crear_sistema(x)

    def _puntos_por_sistema(self):
        return [p for r in guia.requisitos() for p in r.puntos if _con_carpeta_por_sistema(p)]

    def crear_sistema(self, x: Sistema) -> None:
        """Al añadir un sistema, su carpeta en cada punto por sistema que le toca."""
        for p in self._puntos_por_sistema():
            if seguimiento.toca(p, x):
                self.carpeta(p.codigo, x).mkdir(parents=True, exist_ok=True)

    def _renombrar(self, cambios: list[tuple[Path, Path]]) -> None:
        """Renombra (o mueve) todas o ninguna: si una falla, deshace las que ya se hicieron."""
        hechos = []
        try:
            for origen, destino in cambios:
                origen.rename(destino)
                hechos.append((origen, destino))
        except OSError:
            for origen, destino in reversed(hechos):
                destino.rename(origen)
            raise CarpetaOcupada()

    def _carpetas_de(self, nombre: str) -> list[Path]:
        """Las carpetas de un sistema en todos los puntos, esté activo o retirado."""
        base = nombre_seguro(nombre)
        res = []
        for p in self._puntos_por_sistema():
            punto = self.carpeta(p.codigo)
            if punto.is_dir():
                res += [d for d in punto.iterdir() if d.is_dir()
                        and (d.name == base or d.name.startswith(f"{base} (retirado "))]
        return res

    def retirar(self, x: Sistema, hoy: date) -> None:
        """Los archivos del sistema pasan al historial de cada requisito, como «A.5.4.a - ChatGPT -
        2026-10-02 - evaluacion.pdf», y sus carpetas vacías se quitan."""
        base = nombre_seguro(x.nombre)
        carpetas = [d for d in self._carpetas_de(x.nombre) if d.name == base]
        movimientos = []
        for d in carpetas:
            punto = d.parent.name
            historial = self.carpeta_historial(_requisito_de(punto))
            historial.mkdir(exist_ok=True)
            ocupados = set()
            for f in sorted(d.iterdir()):
                if f.is_file():
                    destino = _libre(historial, f"{punto} - {base} - {hoy.isoformat()} - {f.name}")
                    while destino.name in ocupados:  # dos archivos que irían al mismo nombre
                        destino = _libre(historial, f"{destino.stem} (2){destino.suffix}")
                    ocupados.add(destino.name)
                    movimientos.append((f, destino))
        self._renombrar(movimientos)
        for d in carpetas:
            try:
                d.rmdir()  # solo si ha quedado vacía
            except OSError:
                pass

    def activar(self, x: Sistema) -> None:
        """Sus carpetas, de nuevo y vacías. Las de versiones anteriores («… (retirado …)») recuperan el nombre."""
        base = nombre_seguro(x.nombre)
        self._renombrar([(d, d.with_name(base)) for d in self._carpetas_de(x.nombre)
                         if d.name != base and not (d.parent / base).exists()])
        self.crear_sistema(x)

    def renombrar(self, viejo: str, nuevo: str) -> None:
        """Al cambiar el nombre de un sistema, sus carpetas también (con su «(retirado …)» si lo llevan)."""
        a, b = nombre_seguro(viejo), nombre_seguro(nuevo)
        if a == b:
            return
        self._renombrar([(d, d.with_name(b + d.name[len(a):])) for d in self._carpetas_de(viejo)])

    def carpeta(self, punto: str, sistema: Sistema | None = None) -> Path:
        carpeta = self._requisito(_requisito_de(punto)) / punto
        return carpeta / nombre_carpeta(sistema) if sistema else carpeta

    def carpeta_historial(self, requisito: str) -> Path:
        return self._requisito(requisito) / HISTORIAL

    # --- Archivos de un punto ---

    # En los puntos por sistema, cada función recibe además el sistema de la línea

    def archivos(self, punto: str, sistema: Sistema | None = None) -> list[Archivo]:
        return _listar(self.carpeta(punto, sistema))

    def ruta(self, punto: str, nombre: str, sistema: Sistema | None = None) -> Path:
        return _buscar(self.carpeta(punto, sistema), nombre)

    def guardar(self, punto: str, nombre: str, datos: BinaryIO, sistema: Sistema | None = None) -> str:
        """Guarda un archivo subido y devuelve el nombre con que ha quedado."""
        carpeta = self.carpeta(punto, sistema)
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = _libre(carpeta, nombre_seguro(nombre))
        with open(ruta, "wb") as f:
            shutil.copyfileobj(datos, f)
        return ruta.name

    def quitar(self, punto: str, nombre: str, hoy: date, sistema: Sistema | None = None) -> str:
        """Lo pasa al historial como «5.2.a - 2026-10-02 - nombre» (o «A.5.4.a - ChatGPT - 2026-10-02 -
        nombre» si es de un sistema) y devuelve ese nombre."""
        origen = self.ruta(punto, nombre, sistema)
        historial = self.carpeta_historial(_requisito_de(punto))
        historial.mkdir(exist_ok=True)
        delante = f"{punto} - {nombre_seguro(sistema.nombre)}" if sistema else punto
        destino = _libre(historial, f"{delante} - {hoy.isoformat()} - {nombre}")
        origen.rename(destino)
        return destino.name

    def sustituir(self, punto: str, hoy: date, sistema: Sistema | None = None) -> list[str]:
        """Al renovar con archivo nuevo, los que había pasan al historial."""
        return [self.quitar(punto, a.nombre, hoy, sistema) for a in self.archivos(punto, sistema)]

    # --- Historial de un requisito ---

    def historial(self, requisito: str) -> list[Archivo]:
        # Lo más reciente arriba: el nombre lleva la fecha detrás del código del punto
        return sorted(_listar(self.carpeta_historial(requisito)), key=lambda a: a.fecha, reverse=True)

    def ruta_historial(self, requisito: str, nombre: str) -> Path:
        return _buscar(self.carpeta_historial(requisito), nombre)

    def borrar(self, requisito: str, nombre: str) -> None:
        """Borra para siempre. Solo desde el historial, y tras confirmar en la ficha."""
        self.ruta_historial(requisito, nombre).unlink()
