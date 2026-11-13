# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Importa el portal de otra persona a una empresa: su portal.db y su carpeta de pruebas.

    python scripts/importar.py PORTAL.DB CARPETA "EMPRESA" --quien "NOMBRE"

CARPETA es la de pruebas del portal de origen: la que tiene dentro una carpeta por requisito (4.1, 5.2…). EMPRESA tiene
que existir y estar vacía (se crea con scripts/cuentas.py). Lo que en el origen no dice quién lo hizo queda a nombre de
NOMBRE. El original no se toca.

Va al portal de verdad: los datos al MySQL (necesita secretos.env) y los archivos a la carpeta de pruebas elegida en
este ordenador. Con --local, al portal local (datos/).
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from portal import config, cuentas, db, servidor  # noqa: E402
from portal.importar import ErrorImportar, importar  # noqa: E402


def main(argv: list[str]) -> str:
    p = argparse.ArgumentParser(description="Importa el portal de otra persona a una empresa.")
    p.add_argument("portal_db", type=Path)
    p.add_argument("carpeta", type=Path, help="la carpeta de pruebas, con una carpeta por requisito")
    p.add_argument("empresa")
    p.add_argument("--quien", required=True, help="a nombre de quién queda lo que no dice quién lo hizo")
    p.add_argument("--local", action="store_true", help="el portal local (datos/), no el del MySQL")
    a = p.parse_args(argv)

    if a.local:
        datos = config.DATOS_LOCAL
        db.usar_servidor(None)
    else:
        datos = config.DATOS_SERVIDOR
        db.usar_servidor(servidor.leer(config.SECRETOS))
    cuentas.iniciar(datos)
    e = cuentas.empresa(datos, a.empresa)
    if e is None:
        raise ErrorImportar(f"No hay ninguna empresa «{a.empresa}». Créala antes con scripts/cuentas.py.")
    if a.local:
        raiz = datos
    else:
        raiz = config.carpeta_pruebas()
        if raiz is None:
            raise ErrorImportar("No se sabe en qué carpeta van los archivos de pruebas en este ordenador: arranca el portal y elígela (la pide al entrar).")
    bd = cuentas.bd_de(datos, e.slug)
    db.iniciar(bd)
    destino = raiz / e.slug / "pruebas"
    resumen = importar(a.portal_db, a.carpeta, bd, destino, a.quien)
    return f"Importado en «{e.nombre}» (archivos en {destino}):\n{resumen.texto()}"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print(main(sys.argv[1:]))
    except (ErrorImportar, cuentas.ErrorCuentas, servidor.SinConexion) as error:
        print(f"No se ha importado: {error}")
        sys.exit(1)
