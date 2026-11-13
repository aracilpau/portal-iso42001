# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Las cuentas y las empresas del portal. El portal solo las lee: se gestionan desde aquí.

    python scripts/cuentas.py usuarios                          lista las cuentas y sus empresas
    python scripts/cuentas.py empresas                          lista las empresas
    python scripts/cuentas.py crear-usuario CORREO "NOMBRE"     pide la contraseña dos veces
    python scripts/cuentas.py clave CORREO                      cambia la contraseña
    python scripts/cuentas.py quitar CORREO                     ya no puede entrar (lo que hizo se queda)
    python scripts/cuentas.py activar CORREO                    vuelve a poder entrar
    python scripts/cuentas.py crear-empresa "NOMBRE"
    python scripts/cuentas.py renombrar "NOMBRE" "NUEVO"
    python scripts/cuentas.py borrar "NOMBRE"                   para siempre: pide escribir el nombre
    python scripts/cuentas.py asignar CORREO "EMPRESA"          que pueda entrar en esa empresa
    python scripts/cuentas.py desasignar CORREO "EMPRESA"
    python scripts/cuentas.py administrador CORREO              que administre el portal
    python scripts/cuentas.py no-administrador CORREO           que deje de administrarlo (tiene que quedar otro)

Trabaja con el portal instalado en este ordenador: si es «compartido», en el MySQL (necesita secretos.env); si es
«solo en este ordenador», en su carpeta de datos. Con --local, con el portal local de desarrollo (datos/,
arrancar-local.bat); con --prueba, con el de prueba (datos-prueba/). La contraseña se puede dar con --clave
(solo para datos inventados: queda en el historial de la terminal).
"""
import argparse
import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from portal import config, cuentas, db, servidor  # noqa: E402


def pedir_clave(dada: str | None) -> str:
    if dada is not None:
        return dada
    clave = getpass.getpass("Contraseña: ")
    if clave != getpass.getpass("Repítela: "):
        raise cuentas.ErrorCuentas("Las dos contraseñas no coinciden.")
    return clave


def main(argv: list[str], datos: Path | None = None, leer=input, pruebas_en=None) -> str:
    """Hace lo pedido y devuelve qué ha pasado, en llano. `datos`, `leer` y `pruebas_en` (dónde buscar las carpetas de
    pruebas si no están en `datos`: en el portal compartido, la elegida en este ordenador) se cambian en las pruebas."""
    p = argparse.ArgumentParser(prog="cuentas.py", description="Las cuentas y las empresas del portal.")
    p.add_argument("--prueba", action="store_true", help="el portal de prueba (datos-prueba/)")
    p.add_argument("--local", action="store_true", help="el portal local (datos/), no el del MySQL")
    ordenes = p.add_subparsers(dest="orden", required=True)
    ordenes.add_parser("usuarios")
    ordenes.add_parser("empresas")
    o = ordenes.add_parser("crear-usuario")
    o.add_argument("correo"), o.add_argument("nombre"), o.add_argument("--clave")
    o = ordenes.add_parser("clave")
    o.add_argument("correo"), o.add_argument("--clave")
    for orden in ("quitar", "activar"):
        ordenes.add_parser(orden).add_argument("correo")
    ordenes.add_parser("crear-empresa").add_argument("nombre")
    o = ordenes.add_parser("renombrar")
    o.add_argument("nombre"), o.add_argument("nuevo")
    o = ordenes.add_parser("borrar")
    o.add_argument("nombre"), o.add_argument("--confirmar", help="el nombre otra vez, para no preguntarlo")
    for orden in ("administrador", "no-administrador"):
        ordenes.add_parser(orden).add_argument("correo")
    for orden in ("asignar", "desasignar"):
        o = ordenes.add_parser(orden)
        o.add_argument("correo"), o.add_argument("empresa")
    a = p.parse_args(argv)

    if datos is None:
        if a.prueba or a.local:
            datos = RAIZ / "datos-prueba" if a.prueba else config.DATOS_LOCAL
            db.usar_servidor(None)
        elif config.modo() == config.LOCAL:  # instalado «solo en este ordenador»
            datos = config.datos_local()
            db.usar_servidor(None)
        else:
            datos = config.DATOS_SERVIDOR
            db.usar_servidor(servidor.leer(config.SECRETOS))
            pruebas_en = config.carpeta_pruebas
    cuentas.iniciar(datos, prueba=a.prueba)

    if a.orden == "usuarios":
        filas = []
        for u in cuentas.usuarios(datos):
            suyas = ", ".join(e.nombre for e in cuentas.empresas_de(datos, u.id)) or "ninguna"
            admin = " (administrador)" if u.id in cuentas.administradores(datos) else ""
            filas.append(f"- {u.nombre} <{u.correo}>{admin}{'' if u.activo else ' (quitado)'}: {suyas}")
        return "\n".join(filas) or "No hay ninguna cuenta."
    if a.orden == "empresas":
        filas = [f"- {e.nombre} (carpeta {e.slug}){' · entran todos' if e.todos else ''}"
                 for e in cuentas.empresas(datos)]
        return "\n".join(filas) or "No hay ninguna empresa."
    if a.orden == "crear-usuario":
        u = cuentas.crear_usuario(datos, a.correo, a.nombre, pedir_clave(a.clave))
        return f"Cuenta creada: {u.nombre} <{u.correo}>. Asígnale sus empresas con «asignar»."
    if a.orden == "clave":
        cuentas.cambiar_clave(datos, a.correo, pedir_clave(a.clave))
        return f"Contraseña de {a.correo} cambiada."
    if a.orden in ("quitar", "activar"):
        cuentas.activar(datos, a.correo, a.orden == "activar")
        return f"{a.correo}: {'ya puede entrar' if a.orden == 'activar' else 'ya no puede entrar'}."
    if a.orden == "crear-empresa":
        e = cuentas.crear_empresa(datos, a.nombre)
        return f"Empresa creada: {e.nombre} (carpeta {e.slug}). Asígnale usuarios con «asignar»."
    if a.orden == "renombrar":
        e = cuentas.renombrar_empresa(datos, a.nombre, a.nuevo)
        return f"Ahora se llama {e.nombre}."
    if a.orden == "borrar":
        e = cuentas.empresa(datos, a.nombre)
        if e is None:
            raise cuentas.ErrorCuentas(f"No hay ninguna empresa «{a.nombre}».")
        # En el portal compartido sus pruebas están en la carpeta elegida: si no se sabe cuál, quedarían allí, huérfanas
        pruebas = pruebas_en() if pruebas_en else None
        if pruebas_en and pruebas is None:
            raise cuentas.ErrorCuentas("No se sabe en qué carpeta están los archivos de pruebas en este ordenador: "
                                       "arranca el portal y elígela antes de borrar, para que sus pruebas no se queden "
                                       "allí.")
        escrito = a.confirmar if a.confirmar is not None else leer(
            f"Se borrará «{e.nombre}» para siempre, con todo lo suyo (datos y archivos de pruebas). "
            f"Escribe su nombre para confirmarlo: ")
        if escrito.strip() != e.nombre:
            return "No coincide: no se ha borrado nada."
        cuentas.borrar_empresa(datos, e.nombre, pruebas)
        return f"«{e.nombre}» borrada."
    if a.orden in ("administrador", "no-administrador"):
        cuentas.administrar(datos, a.correo, a.orden == "administrador")
        return f"{a.correo} {'ya administra' if a.orden == 'administrador' else 'ya no administra'} el portal."
    if a.orden in ("asignar", "desasignar"):
        cuentas.asignar(datos, a.correo, a.empresa, a.orden == "asignar")
        return f"{a.correo} {'ya puede entrar en' if a.orden == 'asignar' else 'ya no entra en'} {a.empresa}."
    raise AssertionError(a.orden)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # las tildes, también si la salida va a otro programa
    try:
        print(main(sys.argv[1:]))
    except (cuentas.ErrorCuentas, servidor.SinConexion) as error:
        print(f"No se ha hecho: {error}")
        sys.exit(1)
