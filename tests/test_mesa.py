# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El estilo «Mesa de control», el único del portal."""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import db
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 3, 15)


class Reloj:
    def __init__(self, dia):
        self.dia = dia

    def __call__(self):
        return self.dia


@pytest.fixture
def reloj():
    return Reloj(DIA)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd, reloj):
    with en_portal(bd, hoy=reloj) as c:
        yield c


# --- Un solo estilo ---

def test_siempre_sale_mesa_aunque_se_hubiera_elegido_el_clasico(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        c.cookies.set("estilo", "clasico")  # un navegador que eligió el estilo antiguo
        html = c.get("/").text
        assert "mesa.css" in html and "estilo.css" not in html
        assert c.get("/estilo/clasico", follow_redirects=False).status_code == 404
        assert c.get("/static/estilo.css").status_code == 404


def test_ajustes_ya_no_ofrece_elegir_estilo_pero_si_el_tema(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        html = c.get("/ajustes").text
    aspecto = html[html.index('id="aspecto"'):html.index('<details class="avanzadas"')]
    assert "/estilo/" not in aspecto and "Estilo" not in aspecto
    assert 'name="tema" value="oscuro"' in aspecto


def test_el_portal_de_prueba_tambien_lo_dice_en_mesa(bd):
    with en_portal(bd, hoy=lambda: DIA, prueba=True) as c:
        html = c.get("/").text
    assert ">PRUEBA</span>" in html and "<title>PRUEBA · " in html


# --- Inicio ---

def test_el_menu_tiene_los_sitios_y_marca_donde_estas(cliente):
    html = cliente.get("/").text
    menu = html[html.index('<nav class="nav"'):html.index("</nav>")]
    # Cinco apartados; Ajustes, con la rueda de la franja de arriba
    assert [s for s in ("Inicio", "Empresa", "Requisitos", "Declaración", "Inventario", "Actividad", "Ajustes")
            if f">{s}</a>" in menu] == ["Inicio", "Empresa", "Requisitos", "Declaración", "Actividad"]
    franja = html[html.index('class="franja"'):html.index('<header class="barra">')]
    assert 'class="ajustes-icono" href="/ajustes" title="Ajustes"' in franja
    assert 'class="activa" aria-current="page">Inicio</a>' in menu
    # El inventario va dentro de «Empresa»: marca Empresa y tiene su pestaña
    inventario = cliente.get("/inventario").text
    assert 'class="activa" aria-current="page">Empresa</a>' in inventario
    assert 'class="on" aria-current="page">Sistemas de IA</a>' in inventario
    assert 'id="avisos"' not in html  # en el estilo mesa no hay ventana de avisos: son la lista de Inicio


def test_inicio_sin_nada_pendiente(cliente):
    html = cliente.get("/").text
    # Sin nada vencido, pero con lo obligatorio por hacer, no dice «Todo al día»
    assert "Nada vencido <em>ni por vencer</em>" in html and "Nada pendiente por ahora" in html
    assert "Aún te quedan 27 requisitos obligatorios por completar." in html and "Todo <em>al día</em>" not in html


def test_lo_siguiente_ordena_vencidos_vencen_y_recordatorios(cliente, reloj):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")          # vence el 15/03/2027
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "1"})
    cliente.post("/ajustes/antelacion", data={"dias": "30"})
    reloj.dia = date(2027, 3, 1)                                 # 4.3.a vence pronto; el recordatorio toca
    html = cliente.get("/").text
    assert "Te quedan <em>" in html
    tareas = html[html.index('id="tareas"'):html.index("</ol>")]
    assert tareas.index("Vence 15 mar") < tareas.index("Recordatorio")
    assert 'href="/requisitos/4.3#4.3.a"' in tareas
    assert 'action="/avisos/recordatorio/10.1/hecho"' in tareas

    reloj.dia = date(2027, 3, 20)                                # ya vencido
    html = cliente.get("/").text
    assert "1 punto ya ha vencido" in html and ">Vencido</span>" in html

    r = cliente.post("/avisos/recordatorio/10.1/hecho")          # «Hecho» desde Inicio vuelve a Inicio
    assert r.url.path == "/" and "/avisos/recordatorio/10.1/hecho" not in r.text


def test_el_mapa_tiene_los_65_requisitos_con_su_estado(cliente):
    for p in ("4.3.a", "4.3.b", "4.3.c"):
        cliente.post(f"/requisitos/4.3/puntos/{p}/marcar")
    cliente.post("/requisitos/5.2/puntos/5.2.a/marcar")
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    html = cliente.get("/").text
    celdas = re.findall(r'<a class="celda c-(\w+)" href="/requisitos/([\w.]+)"', html)
    assert len(celdas) == 65
    estado = dict((c, e) for e, c in celdas)
    assert estado["4.3"] == "hecho" and estado["5.2"] == "curso" and estado["A.10.4"] == "noaplica"
    assert estado["4.1"] == "pendiente"


def test_ha_pasado_algo_lleva_directo_a_cada_situacion(cliente):
    html = cliente.get("/").text
    bloque = html[html.index('class="pasado"'):]
    for clave in ("persona", "proveedor", "incidente", "empresa", "fuera"):
        assert f'href="/eventos/{clave}"' in bloque


# --- Requisitos: la lista ---

def filas(html):
    return re.findall(r'<tr class="fila[^"]*">\s*<td class="col-cod"><a href="/requisitos/([\w.]+)"', html)


def test_la_lista_filtra_por_estado_y_cuenta_cada_filtro(cliente, reloj):
    for p in ("4.3.a", "4.3.b", "4.3.c"):
        cliente.post(f"/requisitos/4.3/puntos/{p}/marcar")
    cliente.post("/requisitos/5.2/puntos/5.2.a/marcar")
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    todos = cliente.get("/requisitos").text
    assert len(filas(todos)) == 65
    assert re.search(r'aria-current="page">Todos<b>65</b>', todos)
    assert ">Pendientes<b>63</b>" in todos and ">Completos<b>1</b>" in todos and ">No aplican o no hacen falta<b>1</b>" in todos
    assert filas(cliente.get("/requisitos?ver=completos").text) == ["4.3"]
    assert filas(cliente.get("/requisitos?ver=noaplica").text) == ["A.10.4"]
    pendientes = filas(cliente.get("/requisitos?ver=pendientes").text)
    assert "5.2" in pendientes and "4.3" not in pendientes and "A.10.4" not in pendientes

    reloj.dia = date(2027, 3, 20)  # los puntos de la 4.3 han vencido
    vencen = cliente.get("/requisitos?ver=vencen").text
    assert "4.3" in filas(vencen) and "Algo vencido" in vencen


def test_un_filtro_vacio_lo_dice(cliente):
    assert "Ningún requisito en «Completos»." in cliente.get("/requisitos?ver=completos").text


# --- La ficha de un requisito ---

HX = {"HX-Request": "true"}


def test_la_ficha_marca_con_la_casilla_y_se_pinta_sola(cliente):
    ficha = cliente.get("/requisitos/4.3").text
    assert 'hx-post="/requisitos/4.3/puntos/4.3.a/marcar"' in ficha and 'aria-checked="false"' in ficha
    r = cliente.post("/requisitos/4.3/puntos/4.3.a/marcar", headers=HX)
    assert 'id="ficha"' in r.text and "casilla-marcada" in r.text
    assert 'hx-post="/requisitos/4.3/puntos/4.3.a/desmarcar"' in r.text
    assert "Vence el 15/03/2027." in r.text and "/requisitos/4.3/puntos/4.3.a/renovar" in r.text


def test_la_ficha_sube_quita_y_guarda_versiones(cliente):
    cliente.post("/requisitos/5.2/puntos/5.2.a/archivos", files=[("archivos", ("politica.pdf", b"pdf", "application/pdf"))])
    ficha = cliente.get("/requisitos/5.2").text
    assert 'data-soltar="/requisitos/5.2/puntos/5.2.a/archivos"' in ficha  # arrastrar encima del punto
    assert ">politica.pdf</a>" in ficha and "<b>PDF</b>" in ficha
    assert 'hx-post="/requisitos/5.2/puntos/5.2.a/version"' in ficha
    r = cliente.post("/requisitos/5.2/puntos/5.2.a/archivos/politica.pdf/quitar")
    assert "Se ha movido a versiones anteriores como «5.2.a - 2026-03-15 - politica.pdf»" in r.text
    assert "Versiones anteriores (1)" in r.text and "Borrar para siempre" in r.text


def test_la_ficha_tiene_al_lado_la_nota_reabrir_y_lo_ultimo(cliente):
    for p in ("4.3.a", "4.3.b"):
        cliente.post(f"/requisitos/4.3/puntos/{p}/marcar")
    cliente.post("/requisitos/7.2/puntos/7.2.a/marcar")
    ficha = cliente.get("/requisitos/7.2").text
    lado = ficha[ficha.index('<aside class="lado">'):]
    assert 'hx-post="/requisitos/7.2/nota"' in lado and 'id="nota-estado"' in lado
    assert 'data-confirmar="/requisitos/7.2/reabrir"' in lado      # 7.2 se reabre por evento
    assert "marcado como cumplido" in lado and 'href="/actividad?requisito=7.2"' in lado
    r = cliente.post("/requisitos/7.2/nota", data={"texto": "La lleva RR. HH."}, headers=HX)
    assert 'id="nota-estado"' in r.text and "Guardado a las" in r.text


def test_la_ficha_de_un_punto_por_sistema_tiene_una_linea_por_sistema(cliente):
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    ficha = cliente.get("/requisitos/8.4").text
    assert 'id="8.4.a-1"' in ficha and 'data-soltar="/requisitos/8.4/puntos/8.4.a/sistemas/1/archivos"' in ficha
    assert 'hx-post="/requisitos/8.4/puntos/8.4.a/sistemas/1/marcar"' in ficha
    r = cliente.post("/requisitos/8.4/puntos/8.4.a/sistemas/1/marcar", headers=HX)
    assert "Hecho en 1 de 1 IA" in r.text


def test_la_ficha_de_un_control_que_no_aplica(cliente):
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    ficha = cliente.get("/requisitos/A.10.4").text
    assert "No aplica a vuestra empresa." in ficha and "Sin clientes con IA." in ficha
    assert "/marcar" not in ficha and 'data-soltar="' not in ficha  # ni casillas ni subir


# --- Inventario ---

def test_dar_de_alta_un_sistema_y_rellenar_su_ficha_sola(cliente):
    cliente.post("/requisitos/8.2/puntos/8.2.a/marcar")  # algo de toda la empresa que se podría reabrir
    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    assert r.url.path == "/inventario/1"
    assert "De toda la empresa" in r.text and 'action="/inventario/1/reabrir"' in r.text   # la pregunta del alta
    assert 'hx-post="/inventario/1"' in r.text and 'id="estado-para_que"' in r.text
    r = cliente.post("/inventario/1", data={"nombre": "ChatGPT", "tipo": "herramienta", "para_que": "Redactar correos.",
                                            "auto": "1"}, headers=HX)
    assert 'id="estado-para_que" hx-swap-oob="true" class="sello s-ok">Relleno' in r.text
    lista = cliente.get("/inventario").text
    assert 'class="sistema-nombre" href="/inventario/1">ChatGPT</a>' in lista and "1 de 5 apartados rellenos" in lista
    assert 'data-confirmar="/inventario/1/retirar"' in lista


def test_un_sistema_retirado_se_puede_volver_a_activar(cliente):
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    cliente.post("/inventario/1/no-reabrir")
    cliente.post("/inventario/1/retirar")
    lista = cliente.get("/inventario").text
    assert "Retirados" in lista and 'action="/inventario/1/activar"' in lista


# --- Declaración ---

def solo(cliente, control, aplica, porque, origen):
    return cliente.post(f"/declaracion/{control}", headers=HX,
                        data={"aplica": aplica, "porque": porque, "auto": "1", "origen": origen})


def test_la_declaracion_se_decide_y_se_guarda_sola_como_en_el_clasico(cliente):
    html = cliente.get("/declaracion").text
    assert html.count('class="control-form"') == 38 and 'id="declaracion-resumen"' in html
    assert 'hx-select="[id=\'control-A.10.4\']"' in html
    r = solo(cliente, "A.10.4", "no", "", "aplica")             # al elegir la opción, lo que falta destacado
    assert 'class="guardado-estado guardado-pista"' in r.text and r.headers["HX-Reswap"] == "none"
    r = solo(cliente, "A.10.4", "no", "Sin clientes con IA.", "porque")  # al dejar de escribir, se guarda
    assert "Guardado a las" in r.text and r.headers["HX-Reswap"] == "none"
    html = cliente.get("/declaracion").text
    assert "Decididos <strong>1 de 38</strong>" in html and 'class="control no-aplica" id="control-A.10.4"' in html


def test_cambios_y_documento_en_mesa(cliente):
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    cambios = cliente.get("/declaracion/cambios").text
    assert 'aria-current="page">Cambios</a>' in cambios and "Sin clientes con IA." in cambios
    documento = cliente.get("/declaracion/documento").text
    assert 'formaction="/declaracion/documento/guardar"' in documento and "Quedan 37 controles sin decidir" in documento


# --- Ha pasado algo ---

def test_desde_inicio_una_situacion_reabre_lo_elegido(cliente):
    cliente.post("/requisitos/7.2/puntos/7.2.a/marcar")
    html = cliente.get("/eventos/persona").text
    assert "Persona nueva o cambio de puesto" in html and 'value="7.2" checked' in html
    assert 'action="/eventos/persona"' in html
    r = cliente.post("/eventos/persona", data={"requisitos": ["7.2"]})
    assert "reabiertos 7.2" in r.text and 'href="/eventos/proveedor"' in r.text
    assert 'hx-post="/requisitos/7.2/puntos/7.2.a/marcar"' in cliente.get("/requisitos/7.2").text


# --- Actividad, Ajustes y no encontrado ---

def test_la_actividad_se_agrupa_por_dia_y_filtra_por_requisito(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    cliente.post("/requisitos/5.2/puntos/5.2.a/marcar")
    html = cliente.get("/actividad").text
    assert '<li class="registro-dia">15/03/2026</li>' in html and html.count('class="registro-fila"') == 2
    solo = cliente.get("/actividad?requisito=5.2").text
    assert solo.count('class="registro-fila"') == 1 and "5.2.a" in solo


def test_ajustes_en_mesa_guarda_al_cambiar(cliente):
    html = cliente.get("/ajustes").text
    for id_ in ('id="que-avisa"', 'id="preguntar"', 'id="revision"', 'id="aspecto"', 'id="antelacion"', 'id="plazos"'):
        assert id_ in html
    assert html.index('id="aspecto"') < html.index('<details class="avanzadas"') < html.index('id="antelacion"')
    r = cliente.post("/ajustes/antelacion", data={"dias": "45"}, headers=HX)
    assert 'value="45" class="numero"' in r.text and 'id="ajustes"' in r.text


def test_no_encontrado_en_mesa(cliente):
    r = cliente.get("/requisitos/9.9")
    assert r.status_code == 404 and "mesa.css" in r.text and "«9.9»" in r.text


# --- Buscador (Ctrl K) ---

def codigos(html):
    return re.findall(r"<b>([\w.]+)</b>", html)


def test_el_buscador_encuentra_por_codigo_primero_el_requisito(cliente):
    r = cliente.get("/buscar?q=7.2")
    assert codigos(r.text) == ["7.2", "7.2.a", "7.2.b", "7.2.c"]
    assert 'href="/requisitos/7.2" class="sel"' in r.text and 'href="/requisitos/7.2#7.2.a"' in r.text


def test_el_buscador_encuentra_por_palabras_sin_tildes(cliente):
    assert "4.4" in codigos(cliente.get("/buscar?q=gestion").text)        # «Sistema de gestión de la IA»
    proveedores = codigos(cliente.get("/buscar?q=Proveedores").text)
    assert proveedores[0] == "A.10.3"                                        # el título antes que los textos


def test_el_buscador_sin_nada_o_sin_resultados(cliente):
    assert "Escribe un código" in cliente.get("/buscar?q=").text
    assert "Nada con «xyz»." in cliente.get("/buscar?q=xyz").text


def test_cada_pagina_lleva_el_buscador(cliente):
    html = cliente.get("/requisitos").text
    assert '<dialog id="buscador"' in html and 'id="abrir-buscador"' in html


# --- Todas las páginas ---

PAGINAS = ("/", "/requisitos", "/requisitos?ver=pendientes", "/requisitos/4.3", "/requisitos/8.4", "/requisitos/A.10.4",
           "/declaracion", "/declaracion/cambios", "/declaracion/documento", "/inventario", "/inventario/1",
           "/eventos", "/eventos/persona", "/actividad", "/ajustes")


def test_todas_las_paginas_se_abren_en_mesa_sin_selectores_con_puntos(cliente):
    # «#control-A.10.4» no funciona en el navegador: tampoco en el estilo nuevo
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    for url in PAGINAS:
        r = cliente.get(url)
        assert r.status_code == 200, url
        for atributo in re.findall(r'hx-(?:target|select|select-oob|swap-oob)="([^"]*)"', r.text):
            assert not re.search(r"#[\w-]*\.", atributo), (url, atributo)
