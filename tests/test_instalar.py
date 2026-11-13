# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La instalación, lo que se ve la primera vez que se arranca el portal.

Ninguna prueba toca los ajustes de verdad (AppData), tu secretos.env ni ningún MySQL: los ajustes van en una carpeta
temporal y «el MySQL» es SQLite en otra (`usar` devuelve None), con una conexión de mentira.
"""
import json

import pytest
from fastapi.testclient import TestClient

from portal import config, cuentas, instalar
from portal import servidor as srv
from portal.main import crear_app

CUENTA = {"empresa": "Ejemplo S.L.", "nombre": "Ana", "correo": "ana@ejemplo.com", "clave": "clave-larga",
          "repetida": "clave-larga"}
MYSQL = {"host": "mibase.ejemplo.com", "puerto": "3306", "usuario": "portal", "clave": "secreta-del-mysql",
         "base": "iso42001"}


class Conexion:
    """«Probar conexión» de mentira: devuelve el error que se le diga, y apunta con qué se probó."""

    def __init__(self, error=None):
        self.error, self.probados = error, []

    def __call__(self, s):
        self.probados.append(s)
        return self.error


@pytest.fixture
def ajustes(tmp_path):
    return tmp_path / "AppData" / "Portal ISO 42001" / "ajustes.json"


def instalador(tmp_path, ajustes, conexion=None):
    return instalar.Instalador(ajustes=ajustes, probar=conexion or Conexion(), usar=lambda s: None,
                               datos_compartido=tmp_path / "mysql", programa=tmp_path / "programa" / "secretos.env")


@pytest.fixture
def portal(tmp_path, ajustes):
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes))) as c:
        yield c


# --- Piezas: el modo y los ajustes ---

def test_sin_instalar_no_hay_modo(tmp_path, ajustes):
    assert config.modo(ajustes, tmp_path / "no-esta.env") is None


def test_guarda_el_modo_sin_borrar_lo_demas(tmp_path, ajustes):
    config.guardar_ajustes(ajustes, carpeta="C:\\Compartida")
    config.guardar_ajustes(ajustes, modo=config.LOCAL, datos=tmp_path / "Datos")
    assert config.modo(ajustes, tmp_path / "no-esta.env") == config.LOCAL
    assert json.loads(ajustes.read_text(encoding="utf-8"))["carpeta"] == "C:\\Compartida"
    assert config.datos_local(ajustes) == tmp_path / "Datos"


def test_un_portal_de_antes_se_detecta_como_compartido(tmp_path, ajustes):
    # Tenía secretos.env en la carpeta del programa: ya funcionaba con el MySQL
    viejo = tmp_path / "programa" / "secretos.env"
    viejo.parent.mkdir()
    viejo.write_text("MYSQL_SERVIDOR=antes\nMYSQL_USUARIO=u\nMYSQL_CLAVE=c\n", encoding="utf-8")
    assert config.modo(ajustes, viejo) == config.COMPARTIDO
    assert config.secretos_de(ajustes).read_text(encoding="utf-8") == viejo.read_text(encoding="utf-8")
    assert viejo.exists()  # el original se queda, por si acaso
    assert json.loads(ajustes.read_text(encoding="utf-8"))["modo"] == config.COMPARTIDO


def test_la_deteccion_no_pisa_un_secretos_que_ya_estaba(tmp_path, ajustes):
    viejo = tmp_path / "programa" / "secretos.env"
    viejo.parent.mkdir()
    viejo.write_text("MYSQL_SERVIDOR=viejo\n", encoding="utf-8")
    config.secretos_de(ajustes).parent.mkdir(parents=True)
    config.secretos_de(ajustes).write_text("MYSQL_SERVIDOR=nuevo\n", encoding="utf-8")
    config.modo(ajustes, viejo)
    assert config.secretos_de(ajustes).read_text(encoding="utf-8") == "MYSQL_SERVIDOR=nuevo\n"


def test_escribe_secretos_y_se_lee_igual(tmp_path):
    destino = tmp_path / "secretos.env"
    config.escribir_secretos(destino, "mibase.ejemplo.com", 3307, "portal", "c=lave#rara", "otra_base")
    assert srv.leer(destino) == srv.Servidor("mibase.ejemplo.com", 3307, "portal", "c=lave#rara", "otra_base")


def test_la_carpeta_de_datos_por_defecto_esta_en_documentos(ajustes):
    assert config.datos_local(ajustes) == config.documentos() / "Portal ISO 42001"


def test_la_carpeta_de_datos_se_crea_si_no_existe(tmp_path):
    assert config.comprobar_datos(f'"{tmp_path / "Nueva" / "Datos"}"') == tmp_path / "Nueva" / "Datos"
    assert (tmp_path / "Nueva" / "Datos").is_dir()


@pytest.mark.parametrize("ruta, motivo", [("", "Examinar"), ("Documentos\\Portal", "no es una ruta completa")])
def test_una_carpeta_de_datos_que_no_vale(ruta, motivo):
    with pytest.raises(config.CarpetaNoVale, match=motivo):
        config.comprobar_datos(ruta)


# --- Piezas: el MySQL y la primera cuenta ---

@pytest.mark.parametrize("cambio, motivo", [
    ({"host": " "}, "Falta la dirección"),
    ({"clave": "", "base": ""}, "Falta la contraseña, la base de datos"),
    ({"puerto": "tres mil"}, "El puerto tiene que ser un número"),
])
def test_los_datos_del_mysql_incompletos_lo_dicen(cambio, motivo):
    v = {**MYSQL, **cambio}
    with pytest.raises(instalar.ErrorInstalar, match=motivo):
        instalar.servidor_de(v["host"], v["puerto"], v["usuario"], v["clave"], v["base"])


def test_probar_conexion_con_un_servidor_que_no_esta_lo_dice_en_llano():
    # Un puerto de este ordenador donde no hay nada: no sale a internet
    error = instalar.probar_conexion(srv.Servidor("127.0.0.1", 1, "u", "c", "iso42001"))
    assert "No se encuentra el servidor" in error or "No se ha podido conectar" in error


def test_la_primera_cuenta_y_empresa_sin_el_general(tmp_path):
    datos = tmp_path / "datos"
    u, e = instalar.crear_primera(datos, " Ana ", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    assert u.nombre == "Ana" and e.nombre == "Ejemplo S.L."
    assert [x.nombre for x in cuentas.empresas(datos)] == ["Ejemplo S.L."]  # sin el General de siempre
    assert cuentas.puede_entrar(datos, u.id, e.slug)
    assert cuentas.entrar(datos, "ana@ejemplo.com", "clave-larga") is not None


@pytest.mark.parametrize("cambio, motivo", [
    ({"clave": "corta", "repetida": "corta"}, "al menos 8 caracteres"),
    ({"repetida": "otra-distinta"}, "no coinciden"),
    ({"correo": "ana"}, "no tiene forma de correo"),
    ({"empresa": " "}, "Falta el nombre de la empresa"),
    ({"nombre": ""}, "Falta tu nombre"),
])
def test_la_primera_cuenta_mal_escrita_no_crea_nada(tmp_path, cambio, motivo):
    v, datos = {**CUENTA, **cambio}, tmp_path / "datos"
    with pytest.raises(instalar.ErrorInstalar, match=motivo):
        instalar.crear_primera(datos, v["nombre"], v["correo"], v["clave"], v["repetida"], v["empresa"])
    # Nada: o ni siquiera se llegó a crear la carpeta, o está sin cuentas ni empresas
    assert not (datos / "cuentas.db").exists() or (not cuentas.usuarios(datos) and not cuentas.empresas(datos))


def test_si_ya_hay_cuentas_no_crea_otra_primera(tmp_path):
    datos = tmp_path / "datos"
    instalar.crear_primera(datos, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    with pytest.raises(instalar.ErrorInstalar, match="ya tiene cuentas"):
        instalar.crear_primera(datos, "Luis", "luis@ejemplo.com", "clave-larga", "clave-larga", "Otra")


# --- Recorridos: solo en este ordenador ---

def test_la_primera_vez_sale_la_instalacion(portal):
    r = portal.get("/requisitos")
    assert r.url.path == "/instalar"
    assert "Solo en este ordenador" in r.text and "Compartido con mi equipo" in r.text
    assert "Qué hay que instalar" in r.text  # primero se explica la diferencia
    assert "marca-local" not in r.text  # la marca «LOCAL» es la de arrancar-local.bat (se vio en el navegador)
    assert portal.get("/entrar").url.path == "/instalar"


def test_instalar_solo_en_este_ordenador_de_principio_a_fin(tmp_path, ajustes, portal):
    r = portal.post("/instalar/modo", data={"modo": "local"})
    assert r.url.path == "/instalar/datos" and "Portal ISO 42001" in r.text  # propone Documentos\Portal ISO 42001
    r = portal.post("/instalar/datos", data={"ruta": str(tmp_path / "Mis datos")})
    assert r.url.path == "/instalar/cuenta" and "paso 3 de 3" in r.text
    r = portal.post("/instalar/cuenta", data=CUENTA)
    # Ya dentro, en su empresa, empezando el cuestionario
    assert r.url.path == "/empresa/paso/1" and "Ejemplo S.L." in r.text and "Ana" in r.text
    assert config.modo(ajustes, tmp_path / "no-esta.env") == config.LOCAL
    assert config.datos_local(ajustes) == tmp_path / "Mis datos"
    assert [e.nombre for e in cuentas.empresas(tmp_path / "Mis datos")] == ["Ejemplo S.L."]
    assert (tmp_path / "Mis datos" / "ejemplo-s-l" / "pruebas" / "4.1").is_dir()  # sus carpetas, en sus datos
    assert portal.get("/instalar").url.path != "/instalar"  # instalado: la instalación ya no se ve
    assert "LOCAL" not in r.text  # la marca es la de arrancar-local.bat, no la de quien lo usa así


def test_al_volver_a_arrancar_no_pregunta_y_se_entra(tmp_path, ajustes, portal):
    portal.post("/instalar/modo", data={"modo": "local"})
    portal.post("/instalar/datos", data={"ruta": str(tmp_path / "Mis datos")})
    portal.post("/instalar/cuenta", data=CUENTA)
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes))) as otra_vez:
        r = otra_vez.get("/")
        assert r.url.path == "/entrar"
        r = otra_vez.post("/entrar", data={"correo": CUENTA["correo"], "clave": CUENTA["clave"]})
        assert "Ejemplo S.L." in r.text


def test_una_cuenta_mal_escrita_lo_dice_y_guarda_lo_escrito(tmp_path, ajustes, portal):
    portal.post("/instalar/modo", data={"modo": "local"})
    portal.post("/instalar/datos", data={"ruta": str(tmp_path / "Mis datos")})
    r = portal.post("/instalar/cuenta", data={**CUENTA, "repetida": "otra-distinta"})
    assert "no coinciden" in r.text and 'value="Ejemplo S.L."' in r.text and 'value="ana@ejemplo.com"' in r.text
    assert "clave-larga" not in r.text  # la contraseña no se vuelve a enseñar
    assert config.modo(ajustes, tmp_path / "no-esta.env") is None  # sin acabar, sigue sin instalar


def test_saltarse_pasos_lleva_al_principio(portal):
    assert portal.get("/instalar/cuenta").url.path == "/instalar"
    assert portal.post("/instalar/cuenta", data=CUENTA).url.path == "/instalar"
    assert portal.get("/instalar/carpeta").url.path == "/instalar"


# --- Recorridos: compartido con el equipo ---

def compartido_hasta_la_carpeta(portal, carpeta):
    portal.post("/instalar/modo", data={"modo": "compartido"})
    r = portal.post("/instalar/mysql", data=MYSQL)
    assert r.url.path == "/instalar/carpeta"
    return portal.post("/instalar/carpeta", data={"ruta": str(carpeta)})


def test_probar_conexion_dice_si_funciona_o_por_que_no(tmp_path, ajustes):
    conexion = Conexion("El usuario o la contraseña no son correctos.")
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes, conexion))) as c:
        c.post("/instalar/modo", data={"modo": "compartido"})
        r = c.post("/instalar/mysql/probar", data=MYSQL, headers={"HX-Request": "true"})
        assert "El usuario o la contraseña no son correctos." in r.text
        assert conexion.probados[0] == srv.Servidor("mibase.ejemplo.com", 3306, "portal", "secreta-del-mysql", "iso42001")
        conexion.error = None
        assert "Conecta bien" in c.post("/instalar/mysql/probar", data=MYSQL).text
    assert not config.secretos_de(ajustes).exists()  # probar no guarda nada


def test_si_el_mysql_no_conecta_no_sigue_ni_guarda(tmp_path, ajustes):
    conexion = Conexion("No se encuentra el servidor «mibase.ejemplo.com».")
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes, conexion))) as c:
        c.post("/instalar/modo", data={"modo": "compartido"})
        r = c.post("/instalar/mysql", data=MYSQL)
        assert r.url.path == "/instalar/mysql" and "No se encuentra el servidor" in r.text
        assert 'value="mibase.ejemplo.com"' in r.text and "secreta-del-mysql" not in r.text
    assert not config.secretos_de(ajustes).exists()


def test_compartido_con_un_mysql_vacio_de_principio_a_fin(tmp_path, ajustes, portal):
    carpeta = tmp_path / "Teams" / "ISO"
    carpeta.mkdir(parents=True)
    r = compartido_hasta_la_carpeta(portal, carpeta)
    assert r.url.path == "/instalar/cuenta" and "paso 4 de 4" in r.text and "Eres el primero" in r.text
    r = portal.post("/instalar/cuenta", data=CUENTA)
    assert r.url.path == "/empresa/paso/1" and "Ejemplo S.L." in r.text
    # Lo apuntado en este ordenador: el modo, la carpeta y secretos.env, escrito por la instalación
    assert config.modo(ajustes, tmp_path / "no-esta.env") == config.COMPARTIDO
    assert config.carpeta_pruebas(ajustes) == carpeta
    assert srv.leer(config.secretos_de(ajustes)) == srv.Servidor("mibase.ejemplo.com", 3306, "portal",
                                                                 "secreta-del-mysql", "iso42001")
    # Las cuentas, en «el MySQL»; las pruebas, en la carpeta compartida
    assert [e.nombre for e in cuentas.empresas(tmp_path / "mysql")] == ["Ejemplo S.L."]
    assert (carpeta / "ejemplo-s-l" / "pruebas" / "4.1").is_dir()


def test_un_companero_se_une_a_un_equipo_que_ya_existe(tmp_path, ajustes, portal):
    # El MySQL del equipo ya tiene cuentas: no se crea nada, se entra con la que le hizo el administrador
    equipo = tmp_path / "mysql"
    instalar.crear_primera(equipo, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    cuentas.crear_usuario(equipo, "luis@ejemplo.com", "Luis", "clave-de-luis")
    cuentas.asignar(equipo, "luis@ejemplo.com", "Ejemplo S.L.")
    carpeta = tmp_path / "Teams" / "ISO"
    carpeta.mkdir(parents=True)
    r = compartido_hasta_la_carpeta(portal, carpeta)
    assert r.url.path == "/entrar" and "ya está conectado con el de tu equipo" in r.text
    assert portal.get("/instalar/cuenta").url.path == "/entrar"  # no hay «primera cuenta» que crear
    r = portal.post("/entrar", data={"correo": "luis@ejemplo.com", "clave": "clave-de-luis"})
    assert "Ejemplo S.L." in r.text
    assert [u.correo for u in cuentas.usuarios(equipo)] == ["ana@ejemplo.com", "luis@ejemplo.com"]


def test_al_unirse_la_carpeta_de_una_empresa_no_vale(tmp_path, ajustes, portal):
    equipo = tmp_path / "mysql"
    instalar.crear_primera(equipo, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    (tmp_path / "Teams" / "ISO" / "ejemplo-s-l").mkdir(parents=True)
    r = compartido_hasta_la_carpeta(portal, tmp_path / "Teams" / "ISO" / "ejemplo-s-l")
    assert "es la carpeta de la empresa «Ejemplo S.L.»" in r.text
    assert config.modo(ajustes, tmp_path / "no-esta.env") is None


# --- Recorridos: los portales que ya funcionaban ---

def test_un_portal_de_antes_entra_como_siempre_sin_instalacion(tmp_path, ajustes):
    viejo = tmp_path / "programa" / "secretos.env"
    viejo.parent.mkdir()
    viejo.write_text("MYSQL_SERVIDOR=antes\nMYSQL_USUARIO=u\nMYSQL_CLAVE=c\n", encoding="utf-8")
    equipo = tmp_path / "mysql"
    instalar.crear_primera(equipo, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    carpeta = tmp_path / "Teams" / "ISO"
    carpeta.mkdir(parents=True)
    config.guardar_carpeta(str(carpeta), ajustes)  # la que eligió antes
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes))) as c:
        r = c.get("/")
        assert r.url.path == "/entrar" and "Bienvenido" not in r.text
        r = c.post("/entrar", data={"correo": "ana@ejemplo.com", "clave": "clave-larga"})
        assert "Ejemplo S.L." in r.text
    assert config.secretos_de(ajustes).exists()


# --- Recorridos: quien se une a un equipo lo sabe antes ---

def test_la_carpeta_es_el_ultimo_paso_si_el_equipo_ya_existe(tmp_path, ajustes, portal):
    equipo = tmp_path / "mysql"
    instalar.crear_primera(equipo, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    portal.post("/instalar/modo", data={"modo": "compartido"})
    r = portal.post("/instalar/mysql", data=MYSQL)
    assert "paso 3 de 3" in r.text and "Tu equipo ya usa el portal" in r.text
    # Con un error en la carpeta, lo sigue diciendo
    r = portal.post("/instalar/carpeta", data={"ruta": "no-es-una-ruta"})
    assert "paso 3 de 3" in r.text and "Tu equipo ya usa el portal" in r.text


def test_con_un_mysql_vacio_quedan_cuatro_pasos(portal):
    portal.post("/instalar/modo", data={"modo": "compartido"})
    r = portal.post("/instalar/mysql", data=MYSQL)
    assert "paso 3 de 4" in r.text and "Tu equipo ya usa el portal" not in r.text


# --- Recorridos: cambiar los datos del MySQL desde «Sin conexión» ---

def portal_compartido_instalado(tmp_path, ajustes):
    """Un portal compartido que ya funcionaba, con los datos del MySQL de antes en secretos.env."""
    equipo = tmp_path / "mysql"
    instalar.crear_primera(equipo, "Ana", "ana@ejemplo.com", "clave-larga", "clave-larga", "Ejemplo S.L.")
    carpeta = tmp_path / "Teams" / "ISO"
    carpeta.mkdir(parents=True)
    config.guardar_carpeta(str(carpeta), ajustes)
    config.escribir_secretos(config.secretos_de(ajustes), "mibase.ejemplo.com", 3306, "portal", "la-de-antes", "iso42001")
    config.guardar_ajustes(ajustes, modo=config.COMPARTIDO)
    return equipo


def test_sin_conexion_ofrece_cambiar_los_datos_del_mysql(tmp_path, ajustes):
    portal_compartido_instalado(tmp_path, ajustes)
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes))) as c:
        assert "Cambiar los datos del MySQL" in c.get("/sin-conexion").text
        r = c.post("/sin-conexion/mysql")
        assert r.url.path == "/instalar/mysql" and "Cambiar los datos del MySQL" in r.text
        # Vienen los de ahora, salvo la contraseña
        assert 'value="mibase.ejemplo.com"' in r.text and 'value="portal"' in r.text and "la-de-antes" not in r.text
        r = c.post("/instalar/mysql", data={**MYSQL, "clave": "la-nueva"})
        assert r.url.path == "/entrar"  # ya funciona: entra como siempre, sin volver a instalar
    assert srv.leer(config.secretos_de(ajustes)).clave == "la-nueva"
    assert config.modo(ajustes, tmp_path / "no-esta.env") == config.COMPARTIDO


def test_al_cambiar_el_mysql_uno_vacio_no_vale(tmp_path, ajustes):
    portal_compartido_instalado(tmp_path, ajustes)
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes))) as c:
        c.post("/sin-conexion/mysql")
        (tmp_path / "mysql" / "cuentas.db").unlink()  # como si fuera otra base de datos, sin las cuentas del equipo
        r = c.post("/instalar/mysql", data={**MYSQL, "clave": "otra"})
        assert "no tiene las cuentas de tu equipo" in r.text
    assert srv.leer(config.secretos_de(ajustes)).clave == "la-de-antes"


def test_cambiar_el_mysql_se_puede_dejar_como_estaba(tmp_path, ajustes):
    portal_compartido_instalado(tmp_path, ajustes)
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=instalador(tmp_path, ajustes))) as c:
        c.post("/sin-conexion/mysql")
        r = c.post("/instalar/cancelar")
        assert r.url.path == "/entrar"
        assert c.get("/instalar/mysql").url.path != "/instalar/mysql"  # la instalación ya no se ve
    assert srv.leer(config.secretos_de(ajustes)).clave == "la-de-antes"


def test_en_un_portal_local_no_se_cambia_el_mysql(tmp_path, ajustes, portal):
    portal.post("/instalar/modo", data={"modo": "local"})
    portal.post("/instalar/datos", data={"ruta": str(tmp_path / "Mis datos")})
    portal.post("/instalar/cuenta", data=CUENTA)
    assert "Cambiar los datos del MySQL" not in portal.get("/sin-conexion").text
    assert portal.post("/sin-conexion/mysql").status_code == 404
