# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El estilo «Plano»: sus letras van dentro del portal (nada de internet), el modo oscuro tiene todos los colores del
claro, y lo que salió de la revisión de uso (sin corchetes, etiquetas sin borde, la licencia con formato)."""
import re
from pathlib import Path

from conftest import en_portal

RAIZ = Path(__file__).resolve().parent.parent
ESTATICO = RAIZ / "portal" / "static"
CSS = (ESTATICO / "mesa.css").read_text(encoding="utf-8")


def _variables(bloque: str) -> set[str]:
    return set(re.findall(r"(--[\w-]+)\s*:", bloque))


# --- Piezas ---

def test_las_letras_estan_dentro_con_su_licencia():
    letras = re.findall(r'url\("(letras/[^"]+)"\)', CSS)
    assert len(letras) == 3
    for letra in letras:
        assert (ESTATICO / letra).stat().st_size > 50_000, letra
    for licencia in ("OFL-Outfit.txt", "OFL-IBMPlexMono.txt"):
        assert "SIL Open Font License" in (ESTATICO / "letras" / licencia).read_text(encoding="utf-8")


def test_nada_se_carga_de_internet():
    assert not re.search(r"@import|url\(\s*['\"]?https?:", CSS)
    for plantilla in (RAIZ / "portal" / "templates").glob("*.html"):
        html = plantilla.read_text(encoding="utf-8")
        assert not re.search(r"<(?:link|script|img)[^>]+(?:href|src)=\"https?:", html), plantilla.name


def test_el_modo_oscuro_tiene_todos_los_colores_del_claro():
    claro = _variables(CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))])
    claro -= {"--titular", "--texto", "--mono", "--m-teja", "--m-mostaza", "--m-salvia"}  # iguales en los dos
    del_sistema = CSS[CSS.index(":root:not([data-tema=\"claro\"])"):]
    elegido = CSS[CSS.index(":root[data-tema=\"oscuro\"]"):]
    for bloque in (del_sistema, elegido):
        assert claro <= _variables(bloque[:bloque.index("}")]), claro - _variables(bloque[:bloque.index("}")])


def _ultima_regla(selector: str) -> str:
    """La última regla cuyo selector es exactamente ese (la que manda)."""
    sin_comentarios = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    reglas = [trozo.split("{") for trozo in sin_comentarios.split("}") if trozo.count("{") == 1]
    return [cuerpo for sel, cuerpo in reglas if sel.strip() == selector][-1]


def test_los_rotulos_no_llevan_corchetes():
    # La revisión de uso: los rótulos entre corchetes y en mayúsculas parecían de programador
    assert not re.search(r"content:\s*\"\s*[\[\]]", CSS)
    assert "text-transform: none" in _ultima_regla(".antetitulo")


def test_las_etiquetas_no_llevan_borde_como_los_botones():
    # El borde es de lo que se pulsa; las etiquetas, con fondo suave
    for selector in (".etq", ".s-acento", ".s-gris"):
        regla = _ultima_regla(selector)
        assert "border" not in regla.replace("border: 0", "") and "box-shadow" not in regla, selector
        assert "background" in regla, selector


def test_cada_color_que_se_usa_esta_definido():
    usadas = set(re.findall(r"var\((--[\w-]+)", CSS)) - {"--p"}  # --p: el avance de cada cuadro, lo pone la página
    assert usadas <= _variables(CSS), usadas - _variables(CSS)


# --- Recorridos ---

def test_el_portal_sirve_sus_letras(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        for letra in ("Outfit.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
            r = cliente.get(f"/static/letras/{letra}")
            assert r.status_code == 200 and len(r.content) > 50_000, letra


def test_el_saludo_de_inicio_va_en_su_caja(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        html = cliente.get("/").text
    saludo = html[html.index('<section class="saludo">'):html.index("</section>")]
    assert '<div class="mancha"><div class="lamina">' in saludo
    assert "Ver todo lo pendiente" in saludo


def test_la_licencia_se_ve_con_formato_y_con_vuelta_al_portal(tmp_path):
    # La revisión de uso: con «##» y «**» a la vista, la página legal parecía rota
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        html = cliente.get("/licencia").text
    legal = html[html.index('class="licencia-texto"'):]
    assert "<h3>Acceptance</h3>" in legal and "<strong><em>As far as the law allows" in legal
    assert "##" not in legal and "**" not in legal and "](#" not in legal
    assert '<a href="/">← Volver al portal</a>' in html


def test_ajustes_se_ve_con_su_palabra(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as cliente:
        html = cliente.get("/").text
    assert re.search(r'class="ajustes-icono"[^>]*>⚙ Ajustes</a>', html)
