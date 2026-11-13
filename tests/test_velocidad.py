# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Marcar más deprisa con el MySQL. Las lecturas que no dependen unas de otras van a la vez, la ficha nueva
vuelve en la misma respuesta al marcar con la casilla y la casilla cambia en pantalla en cuanto se pulsa.

Las pruebas no tocan el MySQL: lo de «a la vez» se prueba con lecturas de mentira.
"""
import threading
import time
from contextvars import ContextVar

import pytest

from portal import db
from conftest import en_portal

HTMX = {"HX-Request": "true"}


@pytest.fixture
def cliente(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    with en_portal(ruta) as c:
        yield c


@pytest.fixture
def como_en_el_mysql(monkeypatch):
    """Que `a_la_vez` crea que está en el MySQL, sin conectarse a nada."""
    monkeypatch.setattr(db, "_servidor", object())


# --- Piezas: a la vez ---

def test_en_local_van_una_tras_otra():
    orden = []
    assert db.a_la_vez(lambda: orden.append(1) or "a", lambda: orden.append(2) or "b") == ["a", "b"]
    assert orden == [1, 2]


def test_con_el_mysql_van_a_la_vez_y_en_orden(como_en_el_mysql):
    hilos = set()

    def lenta(valor):
        def leer():
            hilos.add(threading.get_ident())
            time.sleep(0.2)  # como un viaje a Irlanda, exagerado
            return valor
        return leer

    antes = time.perf_counter()
    assert db.a_la_vez(*(lenta(i) for i in range(6))) == list(range(6))
    assert time.perf_counter() - antes < 0.6  # una tras otra serían 1,2 s
    assert len(hilos) > 1


def test_cada_lectura_sabe_en_que_peticion_esta(como_en_el_mysql):
    # Quién está dentro y en qué empresa va en variables de la petición, que los hilos no heredan solos
    empresa = ContextVar("empresa")
    empresa.set("alfa")
    assert db.a_la_vez(lambda: empresa.get(), lambda: empresa.get()) == ["alfa", "alfa"]


def test_si_una_lectura_falla_se_entera_quien_las_pidio(como_en_el_mysql):
    def falla():
        raise db.srv.SinConexion("sin internet")
    with pytest.raises(db.srv.SinConexion, match="sin internet"):
        db.a_la_vez(lambda: 1, falla)


# --- Recorridos: marcar con la casilla ---

def test_al_marcar_con_la_casilla_la_ficha_vuelve_en_la_misma_respuesta(cliente):
    r = cliente.post("/requisitos/4.1/puntos/4.1.a/marcar", headers=HTMX, follow_redirects=False)
    assert r.status_code == 200  # sin pasar por otra petición
    assert 'id="ficha"' in r.text and 'class="casilla casilla-marcada"' in r.text
    r = cliente.post("/requisitos/4.1/puntos/4.1.a/desmarcar", headers=HTMX, follow_redirects=False)
    assert r.status_code == 200 and 'class="casilla casilla-marcada"' not in r.text


def test_sin_htmx_sigue_volviendo_a_la_ficha(cliente):
    r = cliente.post("/requisitos/4.1/puntos/4.1.a/marcar", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/requisitos/4.1#4.1.a"


def test_la_ficha_sigue_diciendo_quien_subio_cada_archivo(cliente):
    cliente.post("/requisitos/4.1/puntos/4.1.a/archivos",
                 files=[("archivos", ("contexto.pdf", b"%PDF", "application/pdf"))])
    html = cliente.post("/requisitos/4.1/puntos/4.1.a/marcar", headers=HTMX).text
    assert "Subido por Ana" in html and "Marcado" in html


def test_la_casilla_cambia_al_pulsar_y_vuelve_si_no_se_guarda(cliente):
    html = cliente.get("/requisitos/4.1").text
    assert "htmx:beforeRequest" in html and "cambiarCasilla" in html
    assert "caja.classList.toggle(\"hecho\", marcada)" in html  # el recuadro, verde a la vez que el ✓
    assert "htmx:responseError" in html and "No se ha podido guardar. Vuelve a probar." in html
