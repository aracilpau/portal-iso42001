# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Empresas y usuarios desde el portal, y cambiarse la contraseña."""
import pytest
from fastapi.testclient import TestClient

from portal import cuentas, db
from portal.main import crear_app
from conftest import USUARIO, entrar, preparar_cuentas

LUIS = ("luis@ejemplo.com", "Luis", "clave-de-luis")


@pytest.fixture
def datos(tmp_path):
    datos = tmp_path / "datos"
    db.iniciar(datos / "general" / "portal.db")
    preparar_cuentas(datos)
    cuentas.crear_usuario(datos, *LUIS)
    cuentas.crear_empresa(datos, "Lambda")
    cuentas.crear_empresa(datos, "Beta")
    return datos


@pytest.fixture
def ana(datos):
    """Ana: la primera cuenta, que administra."""
    with TestClient(crear_app(datos)) as c:
        entrar(c, None)
        yield c


def como(datos, usuario):
    c = TestClient(crear_app(datos))
    c.__enter__()
    entrar(c, None, usuario)
    return c


def id_de(datos, correo):
    return cuentas.usuario(datos, correo).id


# --- Piezas: quién administra ---

def test_en_un_portal_de_antes_administra_la_primera_cuenta(datos):
    assert cuentas.administradores(datos) == {id_de(datos, USUARIO[0])}
    assert not cuentas.es_administrador(datos, id_de(datos, LUIS[0]))


def test_tiene_que_quedar_un_administrador(datos):
    with pytest.raises(cuentas.ErrorCuentas, match="al menos un administrador"):
        cuentas.administrar(datos, USUARIO[0], False)
    with pytest.raises(cuentas.ErrorCuentas, match="único administrador"):
        cuentas.activar(datos, USUARIO[0], False)
    cuentas.administrar(datos, LUIS[0])
    cuentas.administrar(datos, USUARIO[0], False)  # con otro, sí
    assert cuentas.administradores(datos) == {id_de(datos, LUIS[0])}


def test_un_administrador_quitado_no_cuenta_como_el_que_queda(datos):
    cuentas.administrar(datos, LUIS[0])
    cuentas.activar(datos, LUIS[0], False)
    with pytest.raises(cuentas.ErrorCuentas, match="al menos un administrador"):
        cuentas.administrar(datos, USUARIO[0], False)


def test_cambiarse_la_propia_pide_la_actual(datos):
    ana_id = id_de(datos, USUARIO[0])
    with pytest.raises(cuentas.ErrorCuentas, match="actual no es correcta"):
        cuentas.cambiar_la_propia(datos, ana_id, "mala", "nueva-larga", "nueva-larga")
    with pytest.raises(cuentas.ErrorCuentas, match="al menos 8"):
        cuentas.cambiar_la_propia(datos, ana_id, USUARIO[2], "corta", "corta")
    with pytest.raises(cuentas.ErrorCuentas, match="no coinciden"):
        cuentas.cambiar_la_propia(datos, ana_id, USUARIO[2], "nueva-larga", "otra-larga")
    cuentas.cambiar_la_propia(datos, ana_id, USUARIO[2], "nueva-larga", "nueva-larga")
    assert cuentas.entrar(datos, USUARIO[0], "nueva-larga") and not cuentas.entrar(datos, USUARIO[0], USUARIO[2])


def test_poner_empresas_deja_solo_las_marcadas(datos):
    cuentas.asignar(datos, LUIS[0], "Lambda")
    cuentas.poner_empresas(datos, LUIS[0], {"beta"})
    suyas = {e.nombre for e in cuentas.empresas_de(datos, id_de(datos, LUIS[0]))}
    assert suyas == {"Beta", "General"}  # el General es de todos: no se toca


# --- Recorridos ---

def test_el_administrador_ve_el_enlace_y_los_demas_no(datos, ana):
    assert 'href="/administrar"' in ana.get("/empresas").text
    luis = como(datos, LUIS)
    assert 'href="/administrar"' not in luis.get("/empresas").text
    assert 'href="/contrasena"' in luis.get("/empresas").text  # cambiarse la suya, todos
    # Aunque escriba la dirección, no entra: como si no existiera
    assert luis.get("/administrar").status_code == 404
    assert luis.post("/administrar/empresa", data={"nombre": "Colada"}).status_code == 404
    assert cuentas.empresa(datos, "Colada") is None


def test_crear_una_cuenta_con_sus_empresas_y_que_entre(datos, ana):
    r = ana.post("/administrar/cuenta", data={"nombre": "Marta", "correo": "marta@ejemplo.com",
                                              "clave": "clave-de-marta", "empresas": ["beta"]})
    assert r.url.path == "/administrar" and "Cuenta creada: Marta" in r.text
    assert "marta@" not in str(r.url)  # en la dirección, su número, no su nombre ni su correo
    marta = como(datos, ("marta@ejemplo.com", "Marta", "clave-de-marta"))
    lista = marta.get("/empresas").text
    assert "Beta" in lista and "Lambda" not in lista  # solo la suya (y el General, que es de todos)


def test_una_cuenta_nueva_mal_escrita_lo_dice_y_guarda_lo_escrito(ana, datos):
    r = ana.post("/administrar/cuenta", data={"nombre": "Marta", "correo": "marta@ejemplo.com", "clave": "corta",
                                              "empresas": ["beta"]})
    assert "al menos 8 caracteres" in r.text and 'value="marta@ejemplo.com"' in r.text
    assert cuentas.usuario(datos, "marta@ejemplo.com") is None
    r = ana.post("/administrar/cuenta", data={"nombre": "Otro", "correo": LUIS[0], "clave": "clave-larga"})
    assert "Ya hay una cuenta con el correo" in r.text


def test_cambiar_en_que_empresas_entra(datos, ana):
    luis = id_de(datos, LUIS[0])
    r = ana.post(f"/administrar/cuenta/{luis}/empresas", data={"empresas": ["lambda", "beta"]})
    assert "Guardado en qué empresas entra Luis" in r.text
    assert {e.slug for e in cuentas.empresas_de(datos, luis)} == {"general", "lambda", "beta"}
    ana.post(f"/administrar/cuenta/{luis}/empresas", data={})  # ninguna marcada
    assert {e.slug for e in cuentas.empresas_de(datos, luis)} == {"general"}


def test_el_administrador_cambia_la_contrasena_de_otro(datos, ana):
    luis = id_de(datos, LUIS[0])
    assert "al menos 8" in ana.post(f"/administrar/cuenta/{luis}/clave", data={"clave": "corta"}).text
    r = ana.post(f"/administrar/cuenta/{luis}/clave", data={"clave": "nueva-de-luis"})
    assert "Contraseña de Luis cambiada" in r.text
    assert cuentas.entrar(datos, LUIS[0], "nueva-de-luis")


def test_quitar_una_cuenta_la_saca_aunque_tenga_el_portal_abierto(datos, ana):
    luis_c = como(datos, LUIS)
    assert luis_c.get("/empresas").url.path == "/empresas"
    r = ana.post(f"/administrar/cuenta/{id_de(datos, LUIS[0])}/entra")  # sin «si»: como la ventana de confirmar
    assert "Luis ya no puede entrar" in r.text and "No puede entrar" in r.text
    assert luis_c.get("/empresas").url.path == "/entrar"
    ana.post(f"/administrar/cuenta/{id_de(datos, LUIS[0])}/entra", data={"si": "1"})
    assert cuentas.entrar(datos, LUIS[0], LUIS[2]) is not None


def test_nombrar_otro_administrador(datos, ana):
    luis = id_de(datos, LUIS[0])
    assert "Luis ya es administrador" in ana.post(f"/administrar/cuenta/{luis}/administrador", data={"si": "1"}).text
    assert 'href="/administrar"' in como(datos, LUIS).get("/empresas").text


def test_el_unico_administrador_no_puede_quitarse(datos, ana):
    yo = id_de(datos, USUARIO[0])
    assert "¿Dejar de ser administrador?" in ana.get("/administrar").text  # en su fila, con confirmación
    for accion in ("entra", "administrador"):
        assert "nombra antes a otro" in ana.post(f"/administrar/cuenta/{yo}/{accion}").text
    assert cuentas.es_administrador(datos, yo) and cuentas.usuario(datos, USUARIO[0]).activo


def test_quitarse_de_administrador_si_hay_otro(datos, ana):
    ana.post(f"/administrar/cuenta/{id_de(datos, LUIS[0])}/administrador", data={"si": "1"})
    yo = id_de(datos, USUARIO[0])
    r = ana.post(f"/administrar/cuenta/{yo}/administrador")  # sin «si»: como la ventana de confirmar
    assert r.url.path == "/empresas" and 'href="/administrar"' not in r.text
    assert not cuentas.es_administrador(datos, yo)
    assert ana.get("/administrar").status_code == 404


def test_quitarse_la_cuenta_si_hay_otro_administrador(datos, ana):
    ana.post(f"/administrar/cuenta/{id_de(datos, LUIS[0])}/administrador", data={"si": "1"})
    r = ana.post(f"/administrar/cuenta/{id_de(datos, USUARIO[0])}/entra")
    assert r.url.path == "/entrar"
    assert cuentas.entrar(datos, USUARIO[0], USUARIO[2]) is None


def test_crear_una_empresa(datos, ana):
    r = ana.post("/administrar/empresa", data={"nombre": "Colada"})
    assert "Empresa creada: Colada" in r.text and cuentas.empresa(datos, "Colada") is not None
    assert "Ya hay una empresa" in ana.post("/administrar/empresa", data={"nombre": "colada"}).text


def test_cambiarse_la_contrasena_desde_el_portal(datos, ana):
    r = ana.post("/contrasena", data={"actual": "mala", "nueva": "nueva-larga", "repetida": "nueva-larga"})
    assert "actual no es correcta" in r.text
    r = ana.post("/contrasena", data={"actual": USUARIO[2], "nueva": "nueva-larga", "repetida": "nueva-larga"})
    assert "Contraseña cambiada" in r.text
    assert cuentas.entrar(datos, USUARIO[0], "nueva-larga")


def test_la_primera_cuenta_de_una_instalacion_administra(tmp_path):
    from portal import instalar
    datos = tmp_path / "nuevo"
    u, _ = instalar.crear_primera(datos, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    cuentas.crear_usuario(datos, *LUIS)
    assert cuentas.administradores(datos) == {u.id}


def test_una_cuenta_quitada_solo_se_puede_volver_a_dejar_entrar(datos, ana):
    luis = id_de(datos, LUIS[0])
    ana.post(f"/administrar/cuenta/{luis}/entra")
    html = ana.get("/administrar").text
    fila = html.split(f'id="cuenta-{luis}"')[1].split("</li>")[0]
    assert "Volver a dejar entrar" in fila and "quién hizo qué" in fila
    for no in ("Cambiar contraseña", "Hacer administrador", "Guardar empresas"):
        assert no not in fila, no
    assert html.index(f'id="cuenta-{id_de(datos, USUARIO[0])}"') < html.index(f'id="cuenta-{luis}"')  # al final


def test_avisa_de_una_cuenta_sin_empresas(datos, ana):
    r = ana.post("/administrar/cuenta", data={"nombre": "Eva", "correo": "eva@ejemplo.com", "clave": "clave-de-eva"})
    assert "Todavía no entra en ninguna empresa" in r.text


def test_el_error_sale_junto_a_lo_que_lo_causa(datos, ana):
    r = ana.post("/administrar/cuenta", data={"nombre": "Luis", "correo": LUIS[0], "clave": "otra-clave"})
    nueva = r.text.split('id="nueva-cuenta"')[1]
    assert "Ya hay una cuenta" in nueva and "Vuelve a escribir la contraseña" in nueva
    assert "Ya hay una cuenta" not in r.text.split('id="nueva-cuenta"')[0]
    assert 'scrollIntoView' in r.text


def test_el_administrador_puede_ver_la_contrasena_que_pone(datos, ana):
    html = ana.get("/administrar").text
    assert 'data-ver="n-clave"' in html  # al crear una cuenta
    assert f'data-ver="clave-{id_de(datos, LUIS[0])}"' in html  # al cambiar la de otro


def test_hacer_o_quitar_administrador_pide_confirmacion(datos, ana):
    luis = id_de(datos, LUIS[0])
    fila = ana.get("/administrar").text.split(f'id="cuenta-{luis}"')[1].split("</li>")[0]
    # Un botón que abre la ventana de confirmar (no un formulario que lo hace sin preguntar), con lo que significa
    assert 'data-titulo="¿Hacer administrador?"' in fila and 'data-si="1"' in fila
    assert "Podrá crear cuentas y empresas" in fila
    assert 'type="submit">Hacer administrador' not in fila
    ana.post(f"/administrar/cuenta/{luis}/administrador", data={"si": "1"})  # lo que envía al confirmar
    fila = ana.get("/administrar").text.split(f'id="cuenta-{luis}"')[1].split("</li>")[0]
    assert 'data-titulo="¿Quitar de administrador?"' in fila and 'data-si="0"' in fila


def test_cambiar_el_nombre_de_una_empresa(datos, ana):
    html = ana.get("/administrar").text
    assert 'data-confirmar="/administrar/empresa/beta/nombre"' in html and 'data-campo="nombre-beta"' in html
    r = ana.post("/administrar/empresa/beta/nombre", data={"nombre": "Beta S.L."})
    assert r.url.path == "/administrar" and "ahora la empresa se llama Beta S.L." in r.text
    assert cuentas.empresa(datos, "beta") == cuentas.Empresa("beta", "Beta S.L.", False)  # la carpeta, la misma
    # Queda en la «Actividad» de esa empresa, con quién lo hizo
    ruta = cuentas.bd_de(datos, "beta")
    linea = db.actividad(ruta, db.el_espacio(ruta)["id"])[0]
    assert linea["detalle"] == "«Beta» → «Beta S.L.»" and linea["quien"] == USUARIO[1]


def test_cambiar_el_nombre_mal_lo_dice_y_no_cambia(datos, ana):
    assert "Falta el nombre nuevo" in ana.post("/administrar/empresa/beta/nombre", data={"nombre": " "}).text
    assert "Ya hay una empresa «lambda»" in ana.post("/administrar/empresa/beta/nombre", data={"nombre": "lambda"}).text
    assert cuentas.empresa(datos, "beta").nombre == "Beta"
    assert ana.post("/administrar/empresa/no-esta/nombre", data={"nombre": "X"}).status_code == 404


def test_solo_el_administrador_cambia_el_nombre(datos):
    luis = como(datos, LUIS)
    assert luis.post("/administrar/empresa/beta/nombre", data={"nombre": "Colada"}).status_code == 404
    assert cuentas.empresa(datos, "beta").nombre == "Beta"
