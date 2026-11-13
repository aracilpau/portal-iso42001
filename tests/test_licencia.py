# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La licencia: su texto, la cabecera de cada fichero de código, el aviso legal de los manuales y el pie de las
pantallas con la página «Licencia», que se ve sin entrar, durante la instalación y sin el MySQL."""
from pathlib import Path

from fastapi.testclient import TestClient

from portal import instalar
from portal.main import crear_app
from tests.conftest import en_portal

RAIZ = Path(__file__).resolve().parent.parent
CABECERA = "Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE)."
CODIGO = ["portal/**/*.py", "guia/__init__.py", "guia/datos.py", "scripts/*.py", "tests/*.py", "portal/templates/*",
          "portal/static/*.css", "portal/static/chat.js", "*.bat"]
AJENOS: set[str] = set()


def codigo_propio() -> list[Path]:
    archivos = {f for patron in CODIGO for f in RAIZ.glob(patron) if f.is_file()}
    return sorted(f for f in archivos if "__pycache__" not in f.parts and f.name not in AJENOS)


# --- Piezas ---

def test_el_texto_de_la_licencia_esta_y_es_el_de_uso_interno():
    texto = (RAIZ / "LICENSE").read_text(encoding="utf-8")
    assert texto.startswith("Required Notice: Copyright ")
    assert "# PolyForm Internal Use License 1.0.0" in texto
    assert "you may not distribute the software" in texto


def test_todo_el_codigo_propio_lleva_la_cabecera():
    sin = [f.relative_to(RAIZ).as_posix() for f in codigo_propio()
           if CABECERA not in "\n".join(f.read_text(encoding="utf-8").splitlines()[:2])]
    assert len(codigo_propio()) > 100
    assert not sin, sin


def test_la_libreria_de_fuera_no_lleva_nuestra_cabecera():
    assert "PolyForm" not in (RAIZ / "portal" / "static" / "htmx.min.js").read_text(encoding="utf-8")


def test_los_manuales_explican_la_licencia():
    for ruta, falta in (("docs/instalar.md", "POR COMPLETAR"), ("docs/en/install.md", "TO BE COMPLETED")):
        texto = (RAIZ / ruta).read_text(encoding="utf-8")
        assert "PolyForm Internal Use 1.0.0" in texto and "`LICENSE`" in texto
        assert falta not in texto
    assert "instalar.md#aviso-legal" in (RAIZ / "docs" / "manual.md").read_text(encoding="utf-8")
    assert "install.md#legal-notice" in (RAIZ / "docs" / "en" / "manual.md").read_text(encoding="utf-8")


# --- Recorridos ---

def test_el_pie_y_la_licencia_se_ven_sin_entrar(tmp_path):
    with TestClient(crear_app(tmp_path / "datos")) as c:
        entrada = c.get("/entrar").text
        assert "Desarrollado en Movired" in entrada and 'href="/licencia"' in entrada
        r = c.get("/licencia")
        assert r.status_code == 200 and "/entrar" not in str(r.url)
        assert "dentro de tu empresa" in r.text and "you may not distribute the software" in r.text


def test_el_pie_sale_dentro_del_portal(tmp_path):
    with en_portal(tmp_path / "datos" / "general" / "portal.db") as c:
        assert 'href="/licencia"' in c.get("/").text


def test_la_licencia_se_ve_durante_la_instalacion(tmp_path):
    ajustes = tmp_path / "AppData" / "ajustes.json"
    inst = instalar.Instalador(ajustes=ajustes, probar=lambda s: None, usar=lambda s: None,
                               datos_compartido=tmp_path / "mysql", programa=tmp_path / "programa" / "secretos.env")
    with TestClient(crear_app(tmp_path / "sin-usar", instalador=inst)) as c:
        assert 'href="/licencia"' in c.get("/instalar").text
        r = c.get("/licencia")
        assert r.status_code == 200 and "/instalar" not in str(r.url)
