# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La lista de requisitos y la ficha de cada uno (solo lectura)."""
import pytest
from fastapi.testclient import TestClient

from portal import guia
from portal.main import crear_app
from conftest import en_portal, entrar


@pytest.fixture
def cliente(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as c:
        yield c


# --- Piezas: la guía preparada para las páginas ---

def test_salen_los_65_requisitos_en_el_orden_de_la_norma():
    codigos = [r.codigo for r in guia.requisitos()]
    assert len(codigos) == 65
    assert codigos[0] == "4.1"
    assert codigos.index("10.2") < codigos.index("A.2.2")  # primero cláusulas, luego Anexo A


def test_los_requisitos_se_agrupan_por_parte_y_bloque():
    partes = guia.por_bloques()
    assert [p for p, _ in partes] == ["Cláusulas 4-10", "Anexo A"]
    total = sum(len(reqs) for _, bloques in partes for _, reqs in bloques)
    assert total == 65
    bloques_clausulas = [b for b, _ in partes[0][1]]
    assert bloques_clausulas[0] == "4 Contexto" and bloques_clausulas[-1] == "10 Mejora"


def test_la_7_3_tiene_sus_3_puntos_de_practica():
    r = guia.requisito("7.3")
    assert [p.codigo for p in r.puntos] == ["7.3.a", "7.3.b", "7.3.c"]
    assert {p.tipo for p in r.puntos} == {"Práctica"}


def test_el_recomendado_sale_como_etiqueta_y_no_en_el_texto():
    p = next(p for p in guia.requisito("4.3").puntos if p.codigo == "4.3.d")
    assert p.recomendado
    assert "recomendado" not in p.texto
    otros = [p for r in guia.requisitos() for p in r.puntos if p.recomendado]
    assert {p.codigo for p in otros} == {"4.3.d", "A.2.2.b", "A.2.2.c"}


def test_los_apoyos_son_codigos_de_requisitos_que_existen():
    p = next(p for p in guia.requisito("7.4").puntos if p.codigo == "7.4.b")
    assert p.apoyos == ["5.2", "7.3"]
    for r in guia.requisitos():
        for p in r.puntos:
            for a in p.apoyos:
                assert guia.requisito(a) is not None, f"{p.codigo} se apoya en {a}"


def test_los_puntos_por_sistema_llevan_su_etiqueta():
    logs = next(p for p in guia.requisito("A.6.2.8").puntos if p.codigo == "A.6.2.8.b")
    assert logs.por_sistema == "Solo IA del producto"
    impacto = guia.requisito("A.5.4").puntos[0]
    assert impacto.por_sistema == "Por sistema"
    assert guia.requisito("4.1").puntos[0].por_sistema == ""


def test_solo_los_controles_llevan_ayuda_de_aplicabilidad():
    assert guia.requisito("A.6.2.8").cuando_aplica
    assert not guia.requisito("9.2").cuando_aplica
    assert sum(1 for r in guia.requisitos() if r.cuando_aplica) == 38


# --- Recorridos: las páginas ---

def test_la_lista_muestra_los_65_requisitos_con_enlace_a_su_ficha(cliente):
    r = cliente.get("/requisitos")
    assert r.status_code == 200
    for req in guia.requisitos():
        assert f'href="/requisitos/{req.codigo}"' in r.text


def test_la_ficha_de_la_9_2_enseña_sus_puntos_y_lo_que_pedira_el_auditor(cliente):
    r = cliente.get("/requisitos/9.2")
    assert r.status_code == 200
    html = r.text
    for cod in ("9.2.a", "9.2.b", "9.2.c", "9.2.d"):
        assert f'id="{cod}"' in html
    assert "Te pedirán:" in html  # lo que pedirá el auditor, en cada punto
    assert "nadie audita su propio trabajo" in html
    assert "¿Aplica a tu empresa?" not in html  # es una cláusula, no un control


def test_la_ficha_de_un_control_enseña_su_ayuda(cliente):
    html = cliente.get("/requisitos/A.6.2.8").text
    assert "Control del Anexo A" in html
    assert "¿Aplica a tu empresa?" in html
    assert "Solo IA del producto" in html


def test_se_apoya_en_enlaza_a_la_otra_ficha(cliente):
    html = cliente.get("/requisitos/7.4").text
    assert '<a href="/requisitos/5.2">5.2</a>' in html


def test_la_4_4_avisa_de_que_es_un_resumen(cliente):
    html = cliente.get("/requisitos/4.4").text
    assert "se cumple al cumplir todos los demás requisitos" in html


def test_un_codigo_que_no_existe_da_no_encontrado(cliente):
    r = cliente.get("/requisitos/99.9")
    assert r.status_code == 404
    assert "No hay ningún requisito <em>«99.9»</em>" in r.text


def test_la_barra_lateral_marca_la_seccion_activa(cliente):
    html = cliente.get("/requisitos").text
    assert 'href="/requisitos" class="activa"' in html


def test_ningun_requisito_depende_de_otro_en_circulo():
    # Si A se apoya en B y B en A, ninguno se podría completar nunca
    from guia import datos
    assert datos.circulos() == []


# --- Las explicaciones en llano: se escriben por bloques; la 4.4 (el resumen de todo) no la lleva ---

def test_la_5_2_tiene_su_explicacion_en_llano_y_cada_punto_su_titulo():
    r = guia.requisito("5.2")
    assert r.llano and r.llano.pide and r.llano.quien and r.llano.empezar
    assert all(p.titulo_llano and p.explicacion for p in r.puntos)
    assert guia.requisito("4.4").llano is None


def test_la_ficha_ensena_la_explicacion_en_llano_donde_la_hay(tmp_path):
    with en_portal(tmp_path / "general" / "portal.db") as c:
        con, sin = c.get("/requisitos/5.2").text, c.get("/requisitos/4.4").text
    assert "Qué pide" in con and "Por dónde empezar" in con
    assert "Que esté hecha para vuestra empresa, no copiada." in con and "usamos ChatGPT para redactar" in con
    assert "Qué pide" not in sin and guia.requisito("4.4").resumen in sin
