# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Entrar con correo y contraseña y trabajar en una empresa."""
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import USUARIO, EnvioDeMentira, entrar, preparar_cuentas
from portal import avisos, cuentas, db
from portal.main import crear_app

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cuentas as programa  # noqa: E402  (scripts/cuentas.py)

DIA = date(2026, 3, 15)
LUIS = ("luis@ejemplo.com", "Luis", "clave-de-luis")


@pytest.fixture
def datos(tmp_path):
    return preparar_cuentas(tmp_path / "datos")


@pytest.fixture
def portal(datos):
    """Dos empresas: Lambda (Ana y Luis) y Sigma (solo Luis), además del General."""
    cuentas.crear_usuario(datos, *LUIS)
    cuentas.crear_empresa(datos, "Lambda")
    cuentas.crear_empresa(datos, "Sigma")
    cuentas.asignar(datos, USUARIO[0], "Lambda")
    cuentas.asignar(datos, LUIS[0], "Lambda")
    cuentas.asignar(datos, LUIS[0], "Sigma")
    with TestClient(crear_app(datos, hoy=lambda: DIA)) as c:
        yield c


# --- Piezas: la contraseña ---

def test_la_contrasena_no_se_guarda_tal_cual(datos):
    con = sqlite3.connect(cuentas.ruta(datos))
    guardada = con.execute("SELECT clave FROM usuario WHERE correo = ?", (USUARIO[0],)).fetchone()[0]
    con.close()
    assert USUARIO[2] not in guardada and guardada.startswith("scrypt$")
    assert cuentas.clave_buena(USUARIO[2], guardada) and not cuentas.clave_buena("otra", guardada)
    assert cuentas.huella("x") != cuentas.huella("x")  # cada una con su sal


def test_entrar_con_la_buena_y_no_con_la_mala(datos):
    assert cuentas.entrar(datos, USUARIO[0], USUARIO[2]).nombre == "Ana"
    assert cuentas.entrar(datos, "ANA@ejemplo.com", USUARIO[2]) is not None  # el correo, sin mayúsculas
    assert cuentas.entrar(datos, USUARIO[0], "mala") is None
    assert cuentas.entrar(datos, "nadie@ejemplo.com", "x") is None
    # Ana es la primera cuenta, así que administra: para quitarla tiene que haber otro administrador
    cuentas.crear_usuario(datos, LUIS[0], "Luis", "x")
    cuentas.administrar(datos, LUIS[0])
    cuentas.activar(datos, USUARIO[0], False)
    assert cuentas.entrar(datos, USUARIO[0], USUARIO[2]) is None  # quitada: no entra
    cuentas.activar(datos, USUARIO[0], True)
    cuentas.cambiar_clave(datos, USUARIO[0], "nueva")
    assert cuentas.entrar(datos, USUARIO[0], "nueva") and not cuentas.entrar(datos, USUARIO[0], USUARIO[2])


def test_usuarios_que_no_se_pueden_crear(datos):
    with pytest.raises(cuentas.ErrorCuentas, match="Ya hay una cuenta"):
        cuentas.crear_usuario(datos, "Ana@Ejemplo.com", "Otra Ana", "x")
    with pytest.raises(cuentas.ErrorCuentas, match="forma de correo"):
        cuentas.crear_usuario(datos, "ana", "Ana", "x")
    with pytest.raises(cuentas.ErrorCuentas, match="Falta la contraseña"):
        cuentas.crear_usuario(datos, "otra@ejemplo.com", "Otra", "")


# --- Piezas: las empresas ---

def test_crear_una_empresa_le_da_su_carpeta(datos):
    e = cuentas.crear_empresa(datos, "Señal Ñ, S.L.")
    assert e.slug == "senal-n-s-l" and not e.todos
    assert cuentas.bd_de(datos, e.slug).exists()
    with pytest.raises(cuentas.ErrorCuentas, match="Ya hay una empresa"):
        cuentas.crear_empresa(datos, "señal ñ, s.l.")
    assert cuentas.crear_empresa(datos, "Senal N S L").slug == "senal-n-s-l-2"  # otro nombre, misma carpeta: no pisa


def test_renombrar_cambia_el_nombre_pero_no_la_carpeta(datos):
    cuentas.crear_empresa(datos, "Lambda")
    cuentas.crear_empresa(datos, "Otra")
    assert cuentas.renombrar_empresa(datos, "Lambda", "Lambda S.L.") == cuentas.Empresa("lambda", "Lambda S.L.", False)
    with pytest.raises(cuentas.ErrorCuentas, match="Ya hay una empresa"):
        cuentas.renombrar_empresa(datos, "Otra", "lambda s.l.")


def test_borrar_una_empresa_se_lleva_su_carpeta(datos):
    e = cuentas.crear_empresa(datos, "De prueba")
    (datos / e.slug / "pruebas" / "5.2").mkdir(parents=True)
    cuentas.asignar(datos, USUARIO[0], "De prueba")
    cuentas.borrar_empresa(datos, "De prueba")
    assert not (datos / e.slug).exists() and cuentas.empresa(datos, "De prueba") is None
    assert [x.slug for x in cuentas.empresas_de(datos, cuentas.usuario(datos, USUARIO[0]).id)] == ["general"]


def test_cada_uno_ve_sus_empresas_y_todos_el_general(datos):
    cuentas.crear_usuario(datos, *LUIS)
    cuentas.crear_empresa(datos, "Lambda")
    cuentas.asignar(datos, LUIS[0], "Lambda")
    luis, ana = cuentas.usuario(datos, LUIS[0]).id, cuentas.usuario(datos, USUARIO[0]).id
    assert [e.nombre for e in cuentas.empresas_de(datos, luis)] == ["General", "Lambda"]
    assert [e.nombre for e in cuentas.empresas_de(datos, ana)] == ["General"]
    assert not cuentas.puede_entrar(datos, ana, "lambda")
    cuentas.asignar(datos, LUIS[0], "Lambda", dentro=False)
    assert [e.nombre for e in cuentas.empresas_de(datos, luis)] == ["General"]


def test_el_general_se_crea_una_vez_y_borrado_no_vuelve(datos):
    assert cuentas.empresas(datos) == [cuentas.Empresa("general", "General", True)]
    cuentas.borrar_empresa(datos, "General")
    cuentas.iniciar(datos)  # como al volver a arrancar el portal
    assert cuentas.empresas(datos) == []


def test_lo_de_antes_pasa_al_general_sin_perder_nada(tmp_path):
    datos = tmp_path / "datos"
    db.iniciar(datos / "portal.db")  # como estaba antes de las empresas: una sola base de datos y pruebas/general/
    db.marcar(datos / "portal.db", 1, "5.2.a", DIA)
    (datos / "pruebas" / "general" / "5.2" / "5.2.a").mkdir(parents=True)
    (datos / "pruebas" / "general" / "5.2" / "5.2.a" / "politica.pdf").write_bytes(b"pdf")
    cuentas.iniciar(datos)
    assert not (datos / "portal.db").exists() and not (datos / "pruebas").exists()
    assert "5.2.a" in db.marcas(datos / "general" / "portal.db", 1)
    assert (datos / "general" / "pruebas" / "5.2" / "5.2.a" / "politica.pdf").read_bytes() == b"pdf"


def test_el_portal_de_prueba_trae_un_usuario_para_entrar(tmp_path):
    cuentas.iniciar(tmp_path, prueba=True)
    correo, _, clave = cuentas.PRUEBA
    assert cuentas.entrar(tmp_path, correo, clave) is not None


# --- Piezas: el programa (scripts/cuentas.py) ---

def test_el_programa_crea_asigna_y_lista(datos):
    assert "Cuenta creada: Luis" in programa.main(["crear-usuario", LUIS[0], "Luis", "--clave", "x"], datos)
    assert "Empresa creada: Lambda (carpeta lambda)" in programa.main(["crear-empresa", "Lambda"], datos)
    programa.main(["asignar", LUIS[0], "Lambda"], datos)
    assert programa.main(["usuarios"], datos).splitlines() == [
        "- Ana <ana@ejemplo.com> (administrador): General", "- Luis <luis@ejemplo.com>: General, Lambda"]
    assert "- General (carpeta general) · entran todos" in programa.main(["empresas"], datos)
    programa.main(["quitar", LUIS[0]], datos)
    assert "(quitado)" in programa.main(["usuarios"], datos)
    with pytest.raises(cuentas.ErrorCuentas, match="No hay ninguna empresa"):
        programa.main(["asignar", LUIS[0], "Nadie"], datos)



def test_el_programa_cambia_la_contrasena_olvidada(datos):  # lo que hace olvide-contrasena.bat
    assert programa.main(["clave", USUARIO[0], "--clave", "nueva-larga"], datos) == f"Contraseña de {USUARIO[0]} cambiada."
    assert cuentas.entrar(datos, USUARIO[0], "nueva-larga") and not cuentas.entrar(datos, USUARIO[0], USUARIO[2])
    with pytest.raises(cuentas.ErrorCuentas):
        programa.main(["clave", "nadie@ejemplo.com", "--clave", "nueva-larga"], datos)

def test_el_programa_solo_borra_si_se_escribe_el_nombre(datos):
    programa.main(["crear-empresa", "Lambda"], datos)
    assert programa.main(["borrar", "Lambda"], datos, leer=lambda _: "lambda") == "No coincide: no se ha borrado nada."
    assert (datos / "lambda").exists()
    assert programa.main(["borrar", "Lambda"], datos, leer=lambda _: "Lambda") == "«Lambda» borrada."
    assert not (datos / "lambda").exists()


def test_en_el_portal_de_verdad_borrar_se_lleva_tambien_su_carpeta_de_teams(datos, tmp_path):
    teams = tmp_path / "Teams"
    programa.main(["crear-empresa", "Lambda"], datos)
    programa.main(["crear-empresa", "Otra"], datos)
    (teams / "lambda" / "pruebas" / "5.2" / "5.2.a").mkdir(parents=True)
    (teams / "lambda" / "pruebas" / "5.2" / "5.2.a" / "politica.pdf").write_bytes(b"pdf")
    (teams / "otra" / "pruebas").mkdir(parents=True)
    assert programa.main(["borrar", "Lambda", "--confirmar", "Lambda"], datos, pruebas_en=lambda: teams) == \
        "«Lambda» borrada."
    assert not (teams / "lambda").exists() and not (datos / "lambda").exists()
    assert (teams / "otra" / "pruebas").is_dir()  # las otras empresas, intactas


def test_sin_la_carpeta_de_pruebas_elegida_no_borra_nada(datos):
    # Si en este ordenador no se sabe dónde están las pruebas, se quedarían allí, huérfanas
    programa.main(["crear-empresa", "Lambda"], datos)
    with pytest.raises(cuentas.ErrorCuentas, match="elígela antes de borrar"):
        programa.main(["borrar", "Lambda", "--confirmar", "Lambda"], datos, pruebas_en=lambda: None)
    assert cuentas.empresa(datos, "Lambda") is not None and (datos / "lambda").exists()


# --- Recorridos: entrar ---

def test_sin_entrar_solo_se_ve_la_entrada(portal):
    for url in ("/", "/requisitos", "/ajustes", "/empresas"):
        r = portal.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/entrar"
    assert portal.post("/requisitos/5.2/puntos/5.2.a/marcar", follow_redirects=False).headers["location"] == "/entrar"
    assert portal.get("/static/mesa.css").status_code == 200
    # Un botón de htmx: que cambie la página entera
    r = portal.post("/requisitos/5.2/nota", data={"texto": "x"}, headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/entrar"


def test_con_la_contrasena_mala_lo_dice(portal):
    r = portal.post("/entrar", data={"correo": USUARIO[0], "clave": "mala"})
    assert "El correo o la contraseña no son correctos." in r.text and 'value="ana@ejemplo.com"' in r.text
    assert portal.get("/", follow_redirects=False).headers["location"] == "/entrar"


def test_al_entrar_salen_solo_tus_empresas(portal):
    entrar(portal, empresa=None)
    html = portal.get("/empresas").text
    assert "Hola, Ana" in html and ">General</button>" in html and ">Lambda</button>" in html
    assert "Sigma" not in html
    # Sin elegir empresa no se entra en las páginas, y en una que no es tuya tampoco, ni escribiendo la dirección
    assert portal.get("/requisitos", follow_redirects=False).headers["location"] == "/empresas"
    assert portal.post("/empresas/sigma").status_code == 404
    assert portal.get("/requisitos", follow_redirects=False).headers["location"] == "/empresas"


def test_la_cabecera_dice_donde_estas_y_se_puede_salir(portal):
    entrar(portal, "lambda")
    html = portal.get("/").text
    assert "<strong>Lambda</strong> · Ana" in html and 'href="/empresas">Cambiar empresa' in html
    assert "· Lambda</p>" in html  # Inicio dice la empresa
    portal.post("/salir")
    assert portal.get("/", follow_redirects=False).headers["location"] == "/entrar"


def test_cada_empresa_tiene_lo_suyo(portal, datos):
    entrar(portal, "lambda", LUIS)
    portal.post("/requisitos/5.2/puntos/5.2.a/marcar")
    portal.post("/requisitos/5.2/puntos/5.2.a/archivos", files=[("archivos", ("politica.pdf", b"pdf", "application/pdf"))])
    assert (datos / "lambda" / "pruebas" / "5.2" / "5.2.a" / "politica.pdf").is_file()
    portal.post("/empresas/sigma")
    ficha = portal.get("/requisitos/5.2").text
    assert "politica.pdf" not in ficha
    assert "5.2.a" not in db.marcas(cuentas.bd_de(datos, "sigma"), 1)
    assert "5.2.a" in db.marcas(cuentas.bd_de(datos, "lambda"), 1)
    portal.post("/empresas/lambda")
    assert "politica.pdf" in portal.get("/requisitos/5.2").text


def test_si_te_quitan_o_borran_tu_empresa_dejas_de_verla(portal, datos):
    entrar(portal, "lambda")
    assert portal.get("/").status_code == 200
    cuentas.asignar(datos, USUARIO[0], "Lambda", dentro=False)
    assert portal.get("/", follow_redirects=False).headers["location"] == "/empresas"
    portal.post("/empresas/general")
    cuentas.administrar(datos, LUIS[0])  # Ana administra: para quitarla tiene que quedar otro
    cuentas.activar(datos, USUARIO[0], False)
    assert portal.get("/", follow_redirects=False).headers["location"] == "/entrar"


def test_al_arrancar_el_portal_hay_que_volver_a_entrar(portal, datos):
    entrar(portal, "lambda")
    galleta = portal.cookies.get("portal_sesion")
    with TestClient(crear_app(datos, hoy=lambda: DIA)) as otro:
        otro.cookies.set("portal_sesion", galleta)
        assert otro.get("/", follow_redirects=False).headers["location"] == "/entrar"


def test_el_chat_consulta_la_empresa_de_la_conversacion(portal):
    entrar(portal, "lambda", LUIS)
    portal.post("/requisitos/7.2/puntos/7.2.a/marcar")
    app = portal.app
    assert "- 7.2.a: cumplido" in app.state.consultas_de("lambda").estado_requisito("7.2")
    assert "- 7.2.a: pendiente" in app.state.consultas_de("sigma").estado_requisito("7.2")


# --- Recorrido: los avisos por correo, uno por empresa ---

def test_un_aviso_por_empresa_con_su_nombre(portal, datos):
    lunes = date(2026, 10, 5)
    for slug in ("lambda", "sigma"):
        bd = cuentas.bd_de(datos, slug)
        for clave, valor in ((avisos.ACTIVADOS, "1"), (avisos.PARA, f"{slug}@ejemplo.com"),
                             (avisos.DESDE, lunes.isoformat())):
            db.guardar_ajuste(bd, 1, clave, valor)
    envio = EnvioDeMentira()
    avisos.ejecutar(datos, lunes, envio)
    # A sus usuarios y a los correos escritos a mano
    assert sorted((c["para"], c["asunto"]) for c in envio.correos) == [
        (["ana@ejemplo.com", "luis@ejemplo.com", "lambda@ejemplo.com"],
         "[Portal ISO 42001 · Lambda] Avisos: esta semana"),
        (["luis@ejemplo.com", "sigma@ejemplo.com"], "[Portal ISO 42001 · Sigma] Avisos: esta semana")]
