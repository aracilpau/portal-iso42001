# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Importar el portal de otra persona a una empresa (su portal.db y su carpeta de pruebas).

El origen se fabrica como uno de antes de los usuarios (sin las columnas de quién hizo cada cosa), con datos
inventados. El destino es local (SQLite): el importador hace lo mismo con el MySQL.
"""
import sqlite3
from datetime import date, datetime

import pytest

from portal import db
from portal.importar import ErrorImportar, importar
from scripts import importar as programa

DIA = date(2026, 10, 7)


def portal_viejo(carpeta):
    """Un portal de antes de los usuarios: dos sistemas, marcas, una línea por sistema, una revisión, la Declaración y archivos."""
    bd = carpeta / "portal.db"
    db.iniciar(bd)
    e = db.el_espacio(bd)["id"]
    a = db.crear_sistema(bd, e, "Asistente de ventas", "producto", DIA)
    b = db.crear_sistema(bd, e, "Claude", "herramienta", DIA)
    db.marcar(bd, e, "4.1.a", DIA)
    db.marcar(bd, e, "5.2.a", DIA)
    db.marcar_linea(bd, e, "A.6.2.2.a", b, DIA)
    db.guardar_revision(bd, e, "A.6.2.2.a", b, "si", "Vale.", "", "", "huella", datetime(2026, 10, 7, 10))
    db.guardar_revision(bd, e, "4.1.a", 0, "no", "Falta.", "", "", "huella", datetime(2026, 10, 7, 11))
    db.decidir(bd, e, "A.2.2", True, "Tenemos política.", "", DIA)
    db.apuntar(bd, e, datetime(2026, 10, 7, 9), "marcado", requisito="4.1", punto="4.1.a")
    db.guardar_ajuste(bd, e, "empresa.nombre", "Empresa Inventada S.L.")
    db.guardar_ajuste(bd, e, "altas_pendientes", f"{a}:nuevo,{b}:nuevo")
    con = sqlite3.connect(bd)  # como antes de los usuarios: sin quién
    for tabla, columna in (("punto_marcado", "marcado_por"), ("punto_sistema", "marcado_por"),
                           ("cambio_aplicabilidad", "quien"), ("actividad", "quien")):
        con.execute(f"ALTER TABLE {tabla} DROP COLUMN {columna}")
    con.execute("UPDATE espacio SET creado = '2026-10-07 16:43:57'")
    con.commit()
    con.close()
    pruebas = carpeta / "pruebas"
    (pruebas / "4.1" / "4.1.a").mkdir(parents=True)
    (pruebas / "4.1" / "4.1.a" / "contexto.docx").write_bytes(b"contexto")
    (pruebas / "4.1" / "historial").mkdir()
    (pruebas / "4.1" / "historial" / "4.1.a - 2026-10-07 - contexto.docx").write_bytes(b"viejo")
    (pruebas / "A.6.2.2" / "A.6.2.2.a" / "Claude").mkdir(parents=True)
    (pruebas / "A.6.2.2" / "A.6.2.2.a" / "Claude" / "uso.pdf").write_bytes(b"%PDF")
    return bd, pruebas


@pytest.fixture
def origen(tmp_path):
    return portal_viejo(tmp_path / "origen")


@pytest.fixture
def destino(tmp_path):
    """Una empresa vacía cuyos sistemas no empiezan en 1: en el MySQL los números los comparten todas."""
    bd = tmp_path / "datos" / "beta" / "portal.db"
    db.iniciar(bd)
    con = sqlite3.connect(bd)
    con.execute("INSERT INTO espacio (slug, nombre, creado) VALUES ('otra', 'otra', '2026-10-14 10:00:00')")
    for i in range(5):
        con.execute("INSERT INTO sistema (espacio_id, nombre, tipo, actualizado_en) VALUES (2, ?, 'producto', '2026-10-14')",
                    (f"De otra {i}",))
    con.commit()
    con.close()
    return bd, tmp_path / "teams" / "beta" / "pruebas"


# --- Piezas ---

def test_importa_todo_a_la_empresa(origen, destino):
    resumen = importar(*origen, *destino, quien="Marta")
    bd, pruebas = destino
    e = db.el_espacio(bd)["id"]
    assert set(db.marcados(bd, e)) == {"4.1.a", "5.2.a"}
    assert db.decisiones(bd, e)["A.2.2"].aplica
    assert db.ajustes(bd, e)["empresa.nombre"] == "Empresa Inventada S.L."
    assert [x.nombre for x in db.sistemas(bd, e)] == ["Asistente de ventas", "Claude"]
    assert resumen.filas["punto_marcado"] == 2 and resumen.archivos == 3


def test_renumera_los_sistemas_y_lo_que_los_nombra(origen, destino):
    importar(*origen, *destino, quien="Marta")
    bd, _ = destino
    e = db.el_espacio(bd)["id"]
    numeros = {x.nombre: x.id for x in db.sistemas(bd, e)}
    assert numeros["Claude"] > 5  # los de la otra empresa ocupaban del 1 al 5
    assert set(db.marcas_sistema(bd, e)) == {("A.6.2.2.a", numeros["Claude"])}
    assert set(db.revisiones(bd, e, ["A.6.2.2.a", "4.1.a"])) == {("A.6.2.2.a", numeros["Claude"]), ("4.1.a", 0)}
    assert db.ajustes(bd, e)["altas_pendientes"] == f"{numeros['Asistente de ventas']}:nuevo,{numeros['Claude']}:nuevo"


def test_lo_que_no_dice_quien_queda_a_nombre_de_quien_se_diga(origen, destino):
    importar(*origen, *destino, quien="Marta")
    bd, _ = destino
    e = db.el_espacio(bd)["id"]
    assert db.marcas(bd, e)["4.1.a"].quien == "Marta"
    assert next(iter(db.marcas_sistema(bd, e).values())).quien == "Marta"
    assert [f["quien"] for f in db.actividad(bd, e)] == ["Marta"]
    assert [f["quien"] for f in db.cambios(bd, e)] == ["Marta"]


def test_el_seguimiento_cuenta_desde_el_origen(origen, destino):
    importar(*origen, *destino, quien="Marta")
    assert db.el_espacio(destino[0])["creado"] == "2026-10-07 16:43:57"


def test_copia_los_archivos_con_historial_y_sistemas(origen, destino):
    importar(*origen, *destino, quien="Marta")
    _, pruebas = destino
    assert (pruebas / "4.1" / "4.1.a" / "contexto.docx").read_bytes() == b"contexto"
    assert (pruebas / "4.1" / "historial" / "4.1.a - 2026-10-07 - contexto.docx").read_bytes() == b"viejo"
    assert (pruebas / "A.6.2.2" / "A.6.2.2.a" / "Claude" / "uso.pdf").read_bytes() == b"%PDF"


def test_el_original_no_cambia(origen, destino):
    bd, _ = origen
    antes = bd.read_bytes()
    importar(*origen, *destino, quien="Marta")
    assert bd.read_bytes() == antes


def test_a_una_empresa_con_datos_no_importa_nada(origen, destino):
    bd, pruebas = destino
    e = db.el_espacio(bd)["id"]
    db.marcar(bd, e, "6.2.a", DIA, "Carlos")
    with pytest.raises(ErrorImportar, match="ya tiene datos"):
        importar(*origen, *destino, quien="Marta")
    assert set(db.marcados(bd, e)) == {"6.2.a"} and db.sistemas(bd, e) == []
    assert not pruebas.exists()


def test_a_una_carpeta_con_archivos_no_importa_nada(origen, destino):
    bd, pruebas = destino
    (pruebas / "4.1").mkdir(parents=True)
    (pruebas / "4.1" / "otro.pdf").write_bytes(b"de antes")
    with pytest.raises(ErrorImportar, match="ya tiene archivos"):
        importar(*origen, *destino, quien="Marta")
    assert db.marcados(bd, db.el_espacio(bd)["id"]) == set()


def test_si_falla_a_mitad_no_queda_nada(origen, destino, monkeypatch):
    # Una línea de actividad que no cabe: se para y no queda nada de lo anterior (ni sistemas ni marcas)
    bd_origen, _ = origen
    con = sqlite3.connect(bd_origen)
    con.execute("INSERT INTO punto_sistema (espacio_id, punto, sistema_id, marcado_en) VALUES (1, 'A.6.2.3.a', 99, '2026-10-07')")
    con.commit()
    con.close()
    with pytest.raises(KeyError):  # el sistema 99 no existe en el origen
        importar(*origen, *destino, quien="Marta")
    bd, pruebas = destino
    e = db.el_espacio(bd)["id"]
    assert db.sistemas(bd, e) == [] and db.marcados(bd, e) == set() and not pruebas.exists()


# --- Recorrido: el programa, en local ---

def test_el_programa_importa_a_una_empresa_del_portal_local(origen, tmp_path, monkeypatch):
    from portal import config, cuentas
    datos = tmp_path / "datos-local"
    monkeypatch.setattr(config, "DATOS_LOCAL", datos)
    cuentas.iniciar(datos)
    cuentas.crear_empresa(datos, "Beta")
    texto = programa.main([str(origen[0]), str(origen[1]), "Beta", "--quien", "Marta", "--local"])
    assert "Importado en «Beta»" in texto and "archivos: 3" in texto
    bd = cuentas.bd_de(datos, "beta")
    assert set(db.marcados(bd, db.el_espacio(bd)["id"])) == {"4.1.a", "5.2.a"}
    assert (datos / "beta" / "pruebas" / "4.1" / "4.1.a" / "contexto.docx").exists()


def test_el_programa_dice_si_la_empresa_no_existe(origen, tmp_path, monkeypatch):
    from portal import config
    monkeypatch.setattr(config, "DATOS_LOCAL", tmp_path / "datos-local")
    with pytest.raises(ErrorImportar, match="No hay ninguna empresa «Nadie»"):
        programa.main([str(origen[0]), str(origen[1]), "Nadie", "--quien", "Marta", "--local"])
