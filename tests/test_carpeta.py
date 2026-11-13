# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""En el portal compartido, las pruebas van en la carpeta que elige cada ordenador.

Ninguna prueba toca los ajustes de verdad (AppData) ni abre la ventana de Windows: los ajustes van en una carpeta
temporal y «Examinar» es de mentira.
"""
import json
import shutil

import pytest

from portal import config, db
from conftest import en_portal

HX = {"HX-Request": "true"}


def subir(cliente, punto, nombre, contenido):
    codigo = punto.rsplit(".", 1)[0]
    return cliente.post(f"/requisitos/{codigo}/puntos/{punto}/archivos",
                        files=[("archivos", (nombre, contenido, "application/octet-stream"))])


# --- Piezas: guardar y leer la carpeta ---

def test_guarda_y_lee_la_carpeta(tmp_path):
    ajustes, carpeta = tmp_path / "AppData" / "Portal ISO 42001" / "ajustes.json", tmp_path / "Compartida"
    carpeta.mkdir()
    assert config.carpeta_pruebas(ajustes) is None  # sin elegir
    assert config.guardar_carpeta(str(carpeta), ajustes) == carpeta
    assert config.carpeta_pruebas(ajustes) == carpeta


def test_guardarla_no_borra_lo_demas_de_los_ajustes(tmp_path):
    ajustes, carpeta = tmp_path / "ajustes.json", tmp_path / "Compartida"
    carpeta.mkdir()
    ajustes.write_text(json.dumps({"modo": "compartido"}), encoding="utf-8")
    config.guardar_carpeta(str(carpeta), ajustes)
    assert json.loads(ajustes.read_text(encoding="utf-8")) == {"modo": "compartido", "carpeta": str(carpeta)}


def test_unos_ajustes_estropeados_cuentan_como_sin_elegir(tmp_path):
    ajustes = tmp_path / "ajustes.json"
    ajustes.write_text("esto no es json", encoding="utf-8")
    assert config.carpeta_pruebas(ajustes) is None


def test_la_ruta_pegada_con_comillas_vale(tmp_path):
    # Windows, con «Copiar como ruta de acceso», la pega entre comillas
    carpeta = tmp_path / "Con espacios en el nombre"
    carpeta.mkdir()
    assert config.comprobar_carpeta(f'  "{carpeta}"  ') == carpeta


@pytest.mark.parametrize("ruta, motivo", [
    ("", "Examinar"),
    ("Documentos\\pruebas", "no es una ruta completa"),
    ("{tmp}\\no-esta", "No se encuentra la carpeta"),
])
def test_una_carpeta_que_no_vale_se_rechaza_con_el_motivo(tmp_path, ruta, motivo):
    with pytest.raises(config.CarpetaNoVale, match=motivo):
        config.comprobar_carpeta(ruta.format(tmp=tmp_path))


def test_un_archivo_no_vale_como_carpeta(tmp_path):
    (tmp_path / "archivo.txt").write_text("no es una carpeta", encoding="utf-8")
    with pytest.raises(config.CarpetaNoVale, match="No se encuentra la carpeta"):
        config.comprobar_carpeta(str(tmp_path / "archivo.txt"))


def test_si_la_carpeta_desaparece_se_recuerda_cual_era(tmp_path):
    ajustes, carpeta = tmp_path / "ajustes.json", tmp_path / "Compartida"
    carpeta.mkdir()
    config.guardar_carpeta(str(carpeta), ajustes)
    carpeta.rmdir()
    assert config.carpeta_pruebas(ajustes) is None and config.carpeta_elegida(ajustes) == carpeta


# --- Recorridos: el portal compartido, con la carpeta elegida ---

class Examinar:
    """La ventana de Windows de mentira: devuelve la carpeta que se le diga (None, como si se cancelara)."""

    def __init__(self, devuelve=None):
        self.devuelve, self.veces = devuelve, 0

    def __call__(self, inicial):
        self.veces += 1
        return self.devuelve


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "datos" / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def ajustes(tmp_path):
    return tmp_path / "AppData" / "ajustes.json"


@pytest.fixture
def compartida(tmp_path):
    carpeta = tmp_path / "Teams" / "ISO"
    carpeta.mkdir(parents=True)
    return carpeta


def test_sin_carpeta_la_pide_al_entrar_antes_de_elegir_empresa(bd, ajustes):
    # Vale para todas las empresas: se pide nada más entrar, no dentro de una
    with en_portal(bd, empresa=None, ajustes_pc=ajustes) as c:
        r = c.get("/empresas")
        assert r.url.path == "/carpeta"
        assert "¿Dónde se guardan los archivos de pruebas?" in r.text and "Examinar" in r.text
        assert "Vale para todas las empresas" in r.text and "<code>general</code>" in r.text
        assert "No se encuentra la carpeta elegida" not in r.text  # la primera vez no hay ninguna perdida
        # Cualquier otra página lleva a elegirla; un botón (htmx), cambiando la página entera
        assert c.post("/empresas/general").url.path == "/carpeta"
        assert c.get("/requisitos").url.path == "/carpeta"
        assert c.get("/requisitos", headers=HX).headers.get("HX-Redirect") == "/carpeta"
        assert c.post("/salir").url.path == "/entrar"  # salir, sí


def test_la_carpeta_de_una_empresa_no_vale(bd, ajustes, compartida):
    (compartida / "general").mkdir()
    with en_portal(bd, empresa=None, ajustes_pc=ajustes) as c:
        r = c.post("/carpeta", data={"ruta": str(compartida / "general")})
        assert "es la carpeta de la empresa «General»" in r.text and str(compartida) in r.text
    assert not ajustes.exists()


def test_al_elegirla_entra_y_lo_subido_va_alli(bd, ajustes, compartida):
    with en_portal(bd, empresa=None, ajustes_pc=ajustes) as c:
        r = c.post("/carpeta", data={"ruta": str(compartida)})
        assert r.url.path == "/empresas"  # y ahora, a elegir empresa
        r = c.post("/empresas/general")
        assert r.status_code == 200 and r.url.path != "/carpeta"
        assert subir(c, "4.1.a", "contexto.pdf", b"%PDF-1.4 de prueba").status_code == 200
        assert c.get("/requisitos/4.1/puntos/4.1.a/archivos/contexto.pdf").content == b"%PDF-1.4 de prueba"
    assert (compartida / "general" / "pruebas" / "4.1" / "4.1.a" / "contexto.pdf").read_bytes() == b"%PDF-1.4 de prueba"
    assert not (bd.parent / "pruebas").exists()  # no en la carpeta de datos, como en local
    assert config.carpeta_pruebas(ajustes) == compartida  # y queda apuntada en este ordenador


def test_con_la_carpeta_ya_elegida_no_pregunta(bd, ajustes, compartida):
    config.guardar_carpeta(str(compartida), ajustes)  # como tras actualizar: los ajustes siguen en AppData
    with en_portal(bd, ajustes_pc=ajustes) as c:
        r = c.get("/")
        assert r.url.path == "/" and "¿Dónde se guardan" not in r.text


def test_examinar_deja_escrita_la_carpeta_elegida(bd, ajustes, compartida):
    examinar = Examinar(str(compartida))
    with en_portal(bd, empresa=None, ajustes_pc=ajustes, examinar=examinar) as c:
        r = c.post("/carpeta/examinar", data={"ruta": ""}, headers=HX)
        assert examinar.veces == 1 and f'value="{compartida}"' in r.text
        assert config.carpeta_pruebas(ajustes) is None  # aún no se ha guardado: falta «Usar esta carpeta»


def test_si_se_cancela_examinar_queda_lo_que_habia(bd, ajustes):
    with en_portal(bd, empresa=None, ajustes_pc=ajustes, examinar=Examinar(None)) as c:
        r = c.post("/carpeta/examinar", data={"ruta": "C:\\lo que habia"}, headers=HX)
        assert 'value="C:\\lo que habia"' in r.text


def test_una_ruta_que_no_vale_lo_dice_y_no_guarda_nada(bd, ajustes, tmp_path):
    with en_portal(bd, empresa=None, ajustes_pc=ajustes) as c:
        c.post("/empresas/general")
        r = c.post("/carpeta", data={"ruta": str(tmp_path / "no-esta")})
        assert r.status_code == 200 and "No se encuentra la carpeta" in r.text
        assert f'value="{tmp_path / "no-esta"}"' in r.text  # lo escrito sigue ahí, para corregirlo
    assert not ajustes.exists()


def test_si_la_carpeta_desaparece_vuelve_a_preguntar(bd, ajustes, compartida, tmp_path):
    config.guardar_carpeta(str(compartida), ajustes)
    with en_portal(bd, ajustes_pc=ajustes) as c:
        assert c.get("/").url.path == "/"
        shutil.rmtree(compartida)  # se deja de sincronizar
        r = c.get("/requisitos")
        assert r.url.path == "/carpeta" and "No se encuentra la carpeta elegida" in r.text and str(compartida) in r.text
        # Elige dónde está ahora, y lo nuevo va allí
        nueva = tmp_path / "Otra"
        nueva.mkdir()
        c.post("/carpeta", data={"ruta": str(nueva)})
        subir(c, "4.1.a", "contexto.pdf", b"en la nueva")
    assert (nueva / "general" / "pruebas" / "4.1" / "4.1.a" / "contexto.pdf").read_bytes() == b"en la nueva"


def test_lo_que_baja_la_sincronizacion_sale_en_el_portal(bd, ajustes, compartida):
    # Un compañero lo sube desde su ordenador: OneDrive lo deja en la carpeta y el portal lo enseña
    config.guardar_carpeta(str(compartida), ajustes)
    with en_portal(bd, ajustes_pc=ajustes) as c:
        (compartida / "general" / "pruebas" / "4.1" / "4.1.a" / "de-ana.docx").write_bytes(b"documento de Ana")
        assert "de-ana.docx" in c.get("/requisitos/4.1").text


def test_en_local_no_hay_carpeta_que_elegir(bd):
    with en_portal(bd) as c:
        assert c.get("/carpeta").status_code == 404
        subir(c, "4.1.a", "contexto.pdf", b"en local")
    assert (bd.parent / "pruebas" / "4.1" / "4.1.a" / "contexto.pdf").read_bytes() == b"en local"
