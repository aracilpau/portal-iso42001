# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La portada de bienvenida: la mancha de colores y «42001» en caracteres. Sale al entrar en una empresa (al entrar
con correo y contraseña o al cambiar de empresa) y al recargar; al moverse por las pantallas, no."""
from pathlib import Path

from fastapi.testclient import TestClient

from portal.main import crear_app
from tests.conftest import USUARIO, preparar_cuentas

RAIZ = Path(__file__).resolve().parent.parent
SI, NO = 'data-ver="si"', 'data-ver="no"'


def entrar_sin_elegir(c):
    r = c.post("/entrar", data={"correo": USUARIO[0], "clave": USUARIO[2]})
    assert "/empresas" in str(r.url)
    return r


# --- Recorridos ---

def test_al_entrar_en_la_empresa_la_primera_pantalla_la_lleva_y_las_siguientes_no(tmp_path):
    with TestClient(crear_app(preparar_cuentas(tmp_path / "datos"))) as c:
        elegir = entrar_sin_elegir(c)
        assert 'id="portada"' not in elegir.text  # al elegir empresa, todavía no
        primera = c.post("/empresas/general")
        assert SI in primera.text and 'class="portada-letras"' in primera.text
        assert 'fillText("42001"' in primera.text and "Hola," not in primera.text  # solo el número, sin textos
        siguiente = c.get("/requisitos").text
        assert NO in siguiente  # al moverse, no (salvo que sea recargar, que lo mira el navegador)


def test_cambiar_de_empresa_y_volver_a_entrar_la_vuelven_a_ensenar(tmp_path):
    with TestClient(crear_app(preparar_cuentas(tmp_path / "datos"))) as c:
        entrar_sin_elegir(c)
        c.post("/empresas/general")
        assert NO in c.get("/").text
        assert SI in c.post("/empresas/general").text  # cambiar de empresa
        c.post("/salir")
        entrar_sin_elegir(c)
        assert SI in c.post("/empresas/general").text


def test_al_recargar_sale_y_antes_de_pintar_la_pagina():
    base = (RAIZ / "portal" / "templates" / "base.html").read_text(encoding="utf-8")
    assert 'nav.type === "reload"' in base
    # va antes que el menú y el contenido: no se ve la pantalla de debajo primero
    assert base.index('id="portada"') < base.index('<header class="barra">') < base.index("{% block contenido %}")
    assert 'p.addEventListener("click", quitar)' in base and '"keydown", quitar' in base
    css = (RAIZ / "portal" / "static" / "mesa.css").read_text(encoding="utf-8")
    regla = css[css.index(".portada {"):css.index("}", css.index(".portada {"))]
    assert "animation" not in regla  # sin aparecer poco a poco (el parpadeo de antes)
    assert "@media (prefers-reduced-motion: reduce) {\n    .portada, .portada::before { animation: none; transition: none; }" in css
