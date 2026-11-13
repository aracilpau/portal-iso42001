# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Quién hizo qué."""
import re
import sqlite3
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from conftest import USUARIO, EnvioDeMentira, entrar, preparar_cuentas
from portal import avisos, cuentas, db
from portal.db import Marca
from portal.main import crear_app

DIA = date(2026, 3, 15)
LUIS = ("luis@ejemplo.com", "Luis", "clave-de-luis")


@pytest.fixture
def datos(tmp_path):
    datos = preparar_cuentas(tmp_path / "datos")
    cuentas.crear_usuario(datos, *LUIS)
    cuentas.crear_empresa(datos, "Alfa")
    cuentas.asignar(datos, USUARIO[0], "Alfa")
    cuentas.asignar(datos, LUIS[0], "Alfa")
    return datos


@pytest.fixture
def portal(datos):
    with TestClient(crear_app(datos, hoy=lambda: DIA, envio=EnvioDeMentira())) as c:
        yield c


@pytest.fixture
def bd(datos):
    return cuentas.bd_de(datos, "alfa")


def quienes(cliente, consulta=""):
    """Quién sale en cada línea de «Actividad», de la más reciente a la más antigua."""
    html = cliente.get("/actividad" + consulta).text
    return re.findall(r'<span class="registro-quien">(.*?)</span>', html)


# --- Piezas: se guarda quién ---

def test_las_marcas_y_los_cambios_guardan_quien(tmp_path):
    ruta = tmp_path / "portal.db"
    db.iniciar(ruta)
    db.marcar(ruta, 1, "5.2.a", DIA, "Ana")
    assert db.marcas(ruta, 1)["5.2.a"] == Marca(DIA, None, "Ana")
    db.renovar(ruta, 1, "5.2.a", date(2026, 4, 1), "Luis")  # renovar lo deja a nombre de quien renueva
    assert db.marcas(ruta, 1)["5.2.a"].quien == "Luis"
    x = db.crear_sistema(ruta, 1, "ChatGPT", "producto", DIA)
    db.marcar_linea(ruta, 1, "A.6.2.2.a", x, DIA, "Ana")
    assert db.marcas_sistema(ruta, 1)[("A.6.2.2.a", x)].quien == "Ana"
    db.decidir(ruta, 1, "A.10.4", False, "Sin clientes.", "", DIA, "Ana")
    db.quitar_decision(ruta, 1, "A.10.4", DIA, "Luis")
    assert [c["quien"] for c in db.cambios(ruta, 1)] == ["Luis", "Ana"]
    db.apuntar(ruta, 1, datetime(2026, 3, 15, 10), "marcado", quien="Ana")
    assert db.actividad(ruta, 1)[0]["quien"] == "Ana"


def test_una_base_de_datos_de_antes_queda_sin_nombre(tmp_path):
    ruta = tmp_path / "portal.db"
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE espacio (id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL,
                              creado TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE actividad (id INTEGER PRIMARY KEY, espacio_id INTEGER NOT NULL, cuando TEXT NOT NULL,
                                accion TEXT NOT NULL, requisito TEXT, punto TEXT, sistema TEXT,
                                detalle TEXT NOT NULL DEFAULT '');
        INSERT INTO espacio (slug, nombre) VALUES ('general', 'General');
        INSERT INTO actividad (espacio_id, cuando, accion, punto) VALUES (1, '2026-03-01T10:00:00', 'marcado', '5.2.a');
    """)
    con.commit()
    con.close()
    db.iniciar(ruta)
    assert db.actividad(ruta, 1)[0]["quien"] == ""


def test_a_quien_van_los_avisos(tmp_path):
    ruta = tmp_path / "portal.db"
    db.iniciar(ruta)
    usuarios = ["ana@ejemplo.com", "luis@ejemplo.com"]
    assert avisos.para(ruta, 1, usuarios) == usuarios  # por defecto, todos los usuarios
    db.guardar_ajuste(ruta, 1, avisos.QUITADOS, "Luis@Ejemplo.com")
    db.guardar_ajuste(ruta, 1, avisos.PARA, "directora@ejemplo.com, ANA@ejemplo.com")
    assert avisos.para(ruta, 1, usuarios) == ["ana@ejemplo.com", "directora@ejemplo.com"]  # sin repetir a Ana


def test_los_usuarios_de_una_empresa(datos):
    assert [u.nombre for u in cuentas.usuarios_de(datos, "alfa")] == ["Ana", "Luis"]
    assert [u.nombre for u in cuentas.usuarios_de(datos, "general")] == ["Ana", "Luis"]  # el General: todos
    cuentas.activar(datos, LUIS[0], False)
    assert [u.nombre for u in cuentas.usuarios_de(datos, "alfa")] == ["Ana"]


# --- Recorridos: dónde sale quién ---

def test_la_ficha_dice_quien_marco_y_quien_subio(portal, datos):
    entrar(portal, "alfa", LUIS)
    portal.post("/requisitos/5.2/puntos/5.2.a/marcar")
    portal.post("/requisitos/5.2/puntos/5.2.a/archivos", files=[("archivos", ("politica.pdf", b"pdf", "application/pdf"))])
    # Uno metido a mano en la carpeta, desde el Explorador
    (datos / "alfa" / "pruebas" / "5.2" / "5.2.a" / "acta.pdf").write_bytes(b"pdf")
    portal.post("/salir")
    entrar(portal, "alfa")
    ficha = portal.get("/requisitos/5.2").text
    assert "Marcado el 15/03/2026 por Luis." in ficha
    assert re.search(r"politica\.pdf</a>\s*.*?<span class=\"sub\">[^<]*· Subido por Luis</span>", ficha, re.S)
    assert re.search(r"acta\.pdf</a>\s*.*?<span class=\"sub\">[^<]*· Añadido en la carpeta</span>", ficha, re.S)
    assert "archivo subido · Luis" in ficha  # lo último del requisito, al lado


def test_lo_subido_antes_de_los_usuarios_va_sin_nombre(portal, bd, datos):
    carpeta = datos / "alfa" / "pruebas" / "5.2" / "5.2.a"
    carpeta.mkdir(parents=True)
    (carpeta / "vieja.pdf").write_bytes(b"pdf")
    db.apuntar(bd, 1, datetime(2026, 3, 1, 10), "subido", requisito="5.2", punto="5.2.a", detalle="vieja.pdf")
    entrar(portal, "alfa")
    ficha = portal.get("/requisitos/5.2").text
    linea = ficha[ficha.index("vieja.pdf</a>"):]
    linea = linea[:linea.index("</span>")]
    assert "Subido por" not in linea and "Añadido en la carpeta" not in linea


def test_actividad_dice_quien_y_se_filtra_por_persona(portal):
    entrar(portal, "alfa", LUIS)
    portal.post("/requisitos/5.2/puntos/5.2.a/marcar")
    portal.post("/salir")
    entrar(portal, "alfa")
    portal.post("/requisitos/4.3/puntos/4.3.a/marcar")
    assert quienes(portal) == ["Ana", "Luis"]
    assert quienes(portal, "?persona=Luis") == ["Luis"]
    html = portal.get("/actividad").text
    assert '<option value="Ana"' in html and '<option value="Luis"' in html


def test_quien_ya_no_esta_sigue_saliendo_con_su_nombre(portal, datos):
    entrar(portal, "alfa", LUIS)
    portal.post("/requisitos/5.2/puntos/5.2.a/marcar")
    portal.post("/salir")
    cuentas.activar(datos, LUIS[0], False)
    entrar(portal, "alfa")
    assert quienes(portal) == ["Luis"]
    assert "Marcado el 15/03/2026 por Luis." in portal.get("/requisitos/5.2").text


def test_los_cambios_de_la_declaracion_dicen_quien(portal):
    entrar(portal, "alfa")
    portal.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    html = portal.get("/declaracion/cambios").text
    assert "Sin clientes con IA. <span class=\"sub\">· Ana</span>" in html


# --- Recorrido: los avisos llegan a los usuarios, que pueden quitarse ---

def test_en_ajustes_cada_usuario_con_su_casilla(portal, bd):
    entrar(portal, "alfa")
    html = portal.get("/ajustes").text
    for correo in ("ana@ejemplo.com", "luis@ejemplo.com"):
        assert f'name="recibe" value="{correo}" checked' in html
    # Luis se quita
    portal.post("/ajustes/correo", data={"activado": "1", "recibe": ["ana@ejemplo.com"], "para": "", "cuenta": ""})
    html = portal.get("/ajustes").text
    assert 'name="recibe" value="ana@ejemplo.com" checked' in html
    assert 'name="recibe" value="luis@ejemplo.com" >' in html
    assert db.ajuste(bd, 1, avisos.QUITADOS, "") == "luis@ejemplo.com"


def test_el_aviso_va_a_los_usuarios_que_no_se_han_quitado(datos, bd):
    envio = EnvioDeMentira()
    with TestClient(crear_app(datos, hoy=lambda: DIA, envio=envio)) as c:
        entrar(c, "alfa")
        c.post("/ajustes/correo", data={"activado": "1", "recibe": ["ana@ejemplo.com"], "para": "dire@ejemplo.com"})
        c.post("/ajustes/correo/prueba")
        assert envio.correos[-1]["para"] == ["ana@ejemplo.com", "dire@ejemplo.com"]
        assert quienes(c)[0] == "Ana"  # el aviso de prueba lo manda quien lo pulsa
    # Uno nuevo en la empresa lo recibe sin hacer nada; el de la tarea de Windows lo firma «el portal»
    cuentas.crear_usuario(datos, "eva@ejemplo.com", "Eva", "x")
    cuentas.asignar(datos, "eva@ejemplo.com", "Alfa")
    lunes = date(2026, 10, 5)
    db.guardar_ajuste(bd, 1, avisos.DESDE, lunes.isoformat())
    avisos.ejecutar(datos, lunes, envio)
    assert envio.correos[-1]["para"] == ["ana@ejemplo.com", "eva@ejemplo.com", "dire@ejemplo.com"]
    assert db.actividad(bd, 1)[0]["quien"] == db.EL_PORTAL
